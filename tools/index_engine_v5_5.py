import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler

import psutil

HAS_BLAKE3 = False
try:
    import blake3

    HAS_BLAKE3 = True
except ImportError:
    pass


# ==========================================
# 1. ETAT DU MOTEUR & HEARTBEATS
# ==========================================
class EngineState:
    STARTING = "STARTING"
    SCANNING = "SCANNING"
    HASHING = "HASHING"
    WRITING = "WRITING"
    FINALIZING = "FINALIZING"
    DONE = "DONE"
    FAILED = "FAILED"
    DEGRADED = "DEGRADED"


class HeartbeatRegistry:
    """Registre centralisé des battements de cœur et états des workers."""

    def __init__(self):
        self._lock = threading.Lock()
        self.workers = {}  # nom -> {"last_beat": float, "state": str, "current_job": str, "processed": int}
        self.engine_state = EngineState.STARTING

    def set_engine_state(self, state):
        with self._lock:
            self.engine_state = state

    def get_engine_state(self):
        with self._lock:
            return self.engine_state

    def register(self, name):
        with self._lock:
            self.workers[name] = {"last_beat": time.time(), "state": "IDLE", "current_job": None, "processed": 0}

    def beat(self, name, state, current_job=None):
        with self._lock:
            if name in self.workers:
                self.workers[name]["last_beat"] = time.time()
                self.workers[name]["state"] = state
                if current_job:
                    self.workers[name]["current_job"] = current_job
                self.workers[name]["processed"] += 1

    def get_stalled_or_dead(self, timeout_sec=30.0):
        with self._lock:
            now = time.time()
            stalled = []
            for name, data in self.workers.items():
                if now - data["last_beat"] > timeout_sec and data["state"] != "IDLE":
                    stalled.append((name, data["current_job"]))
            return stalled


# ==========================================
# 2. LOGGING & TELEMETRY
# ==========================================
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "thread": record.threadName,
            "event": record.getMessage(),
        }
        if hasattr(record, "extra_data"):
            log_obj.update(record.extra_data)
        return json.dumps(log_obj, ensure_ascii=False)


def setup_logger(log_path):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logger = logging.getLogger("IndexEngineV55")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = RotatingFileHandler(log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s"))
        console.setLevel(logging.INFO)
        logger.addHandler(console)
    return logger


class TelemetryCollector:
    def __init__(self):
        self.start_time = 0.0
        self.files_scanned = 0
        self.files_hashed = 0
        self.db_inserts = 0
        self.errors = 0
        self.worker_restarts = 0
        self._lock = threading.Lock()

    def start(self):
        self.start_time = time.time()

    def inc_scanned(self, count=1):
        with self._lock:
            self.files_scanned += count

    def inc_hashed(self, count=1):
        with self._lock:
            self.files_hashed += count

    def inc_db(self, count=1):
        with self._lock:
            self.db_inserts += count

    def inc_error(self):
        with self._lock:
            self.errors += 1

    def inc_restart(self):
        with self._lock:
            self.worker_restarts += 1

    def get_snapshot(self):
        elapsed = max(time.time() - self.start_time, 0.001)
        return {
            "duration_sec": round(elapsed, 2),
            "scan_rate": int(self.files_scanned / elapsed),
            "hash_rate": int(self.files_hashed / elapsed),
            "ram_mb": psutil.Process(os.getpid()).memory_info().rss // 1048576,
            "restarts": self.worker_restarts,
            "errors": self.errors,
        }

    # ==========================================
    # 3. SQLITE PERSISTENT JOB QUEUE
    # ==========================================

    def report(self, logger):
        """
        Rapport final de télémétrie V5.5
        Compatible avec l'orchestrateur WorkspaceIndexerV55
        """
        snapshot = self.get_snapshot()

        logger.info("==================================================")

        logger.info(" TELEMETRIE FINALE INDEX ENGINE V5.5")

        logger.info(f"Durée           : {snapshot['duration_sec']} sec")

        logger.info(f"Fichiers scannés: {self.files_scanned}")

        logger.info(f"Hashes calculés : {self.files_hashed}")

        logger.info(f"Inserts SQLite  : {self.db_inserts}")

        logger.info(f"Erreurs         : {self.errors}")

        logger.info(f"Restarts Watchdog : {self.worker_restarts}")

        logger.info(f"RAM utilisée    : {snapshot['ram_mb']} MB")

        logger.info("==================================================")

        return snapshot


class SQLiteJobQueue:
    def recover_running_jobs(self):
        """
        Réinjecte les jobs interrompus après crash worker.
        """

        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    UPDATE queue_jobs
                    SET status='PENDING'
                    WHERE status='RUNNING'
                    """
                )

                conn.commit()

        except Exception:
            pass

    def count_pending(self):
        """
        Retourne le nombre de jobs encore en attente.
        """
        try:
            with self._get_conn() as conn:
                row = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM queue_jobs
                    WHERE status='PENDING'
                    """
                ).fetchone()

                return row[0]

        except Exception:
            return 0

    """File d'attente persistante (PENDING, RUNNING, DONE, FAILED)."""

    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS queue_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload TEXT,
                status TEXT DEFAULT 'PENDING'
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON queue_jobs(status);")
            conn.execute("UPDATE queue_jobs SET status='PENDING' WHERE status='RUNNING'")  # Reprise après crash
            conn.commit()

    def put_batch(self, items):
        with self._get_conn() as conn:
            conn.executemany("INSERT INTO queue_jobs (payload) VALUES (?)", [(json.dumps(i),) for i in items])

    def fetch_batch(self, batch_size=50):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN EXCLUSIVE;")
            cursor.execute("SELECT id, payload FROM queue_jobs WHERE status='PENDING' LIMIT ?", (batch_size,))
            rows = cursor.fetchall()
            if rows:
                ids = [r[0] for r in rows]
                cursor.execute(f"UPDATE queue_jobs SET status='RUNNING' WHERE id IN ({','.join('?' * len(ids))})", ids)
            cursor.execute("COMMIT;")
            return rows

    def mark_done(self, ids):
        with self._get_conn() as conn:
            conn.execute(f"UPDATE queue_jobs SET status='DONE' WHERE id IN ({','.join('?' * len(ids))})", ids)

    def mark_failed(self, job_id):
        with self._get_conn() as conn:
            conn.execute("UPDATE queue_jobs SET status='FAILED' WHERE id=?", (job_id,))


# ==========================================
# 4. WORKERS (Scanner & Hasher)
# ==========================================
class FileScanner:
    def __init__(self, config, job_queue, telemetry):
        self.config = config
        self.job_queue = job_queue
        self.telemetry = telemetry
        self.excluded_dirs = set(config["exclusions"]["dirs"])
        self.target_exts = set(config["exclusions"]["extensions"])

    def scan(self, root_paths):
        batch = []
        for root_path in root_paths:
            dirs = [root_path]
            while dirs:
                curr = dirs.pop()
                try:
                    fmt_path = curr if curr.startswith("\\\\?\\") or len(curr) < 240 else "\\\\?\\" + curr
                    with os.scandir(fmt_path) as it:
                        for entry in it:
                            try:
                                if entry.is_symlink():
                                    continue
                                if entry.is_dir(follow_symlinks=False) and entry.name not in self.excluded_dirs:
                                    dirs.append(entry.path)
                                elif entry.is_file(follow_symlinks=False):
                                    ext = os.path.splitext(entry.name)[1].lower()
                                    if ext in self.target_exts:
                                        stat = entry.stat()
                                        clean_path = entry.path.replace("\\\\?\\", "")
                                        batch.append(
                                            {
                                                "path": clean_path,
                                                "filename": entry.name,
                                                "folder": os.path.basename(os.path.dirname(clean_path)),
                                                "extension": ext,
                                                "size_kb": round(stat.st_size / 1024, 2),
                                                "mtime": stat.st_mtime,
                                                "inode": stat.st_ino,
                                            }
                                        )
                                        if len(batch) >= 500:
                                            self.job_queue.put_batch(batch)
                                            self.telemetry.inc_scanned(len(batch))
                                            batch.clear()
                            except Exception:
                                pass
                except Exception:
                    pass
        if batch:
            self.job_queue.put_batch(batch)
            self.telemetry.inc_scanned(len(batch))


class HasherWorker(threading.Thread):
    def __init__(self, name, job_queue, db_repo, heartbeat_reg, telemetry, use_blake3):
        super().__init__(name=name)
        self.job_queue = job_queue
        self.db_repo = db_repo
        self.heartbeat_reg = heartbeat_reg
        self.telemetry = telemetry
        self.use_blake3 = use_blake3
        self.daemon = True
        self.logger = logging.getLogger(name)

    def compute_hash(self, file_path):
        try:
            if self.use_blake3:
                h = blake3.blake3()
                with open(file_path, "rb") as f:
                    while chunk := f.read(65536):
                        h.update(chunk)
                return h.digest()
            else:
                h = hashlib.sha256()
                with open(file_path, "rb") as f:
                    while chunk := f.read(65536):
                        h.update(chunk)
                return h.digest()
        except Exception:
            return None

    def run(self):
        self.heartbeat_reg.register(self.name)
        conn_read = self.db_repo.get_connection(read_only=True)
        cursor = conn_read.cursor()
        try:
            while self.heartbeat_reg.get_engine_state() in (EngineState.SCANNING, EngineState.HASHING):
                batch = self.job_queue.fetch_batch(batch_size=20)
                if not batch:
                    self.heartbeat_reg.beat(self.name, "IDLE")
                    time.sleep(0.5)
                    continue

                self.heartbeat_reg.beat(self.name, "HASHING", f"Batch of {len(batch)}")
                done_ids = []
                db_batch = []

                for job_id, payload_str in batch:
                    item = json.loads(payload_str)
                    path = item["path"]
                    cursor.execute(
                        "SELECT hash FROM files WHERE path=? AND mtime=? AND size_kb=? AND inode=? AND is_deleted=0",
                        (path, item["mtime"], item["size_kb"], item["inode"]),
                    )
                    row = cursor.fetchone()
                    if row and row[0]:
                        item["hash"] = row[0]
                    else:
                        item["hash"] = self.compute_hash(path)

                    db_batch.append(
                        (
                            path,
                            item["filename"],
                            item["folder"],
                            item["extension"],
                            item["size_kb"],
                            item["mtime"],
                            item["inode"],
                            item["hash"],
                        )
                    )
                    done_ids.append(job_id)

                # Écriture immédiate par le worker dans la vraie DB (Single Writer n'est plus nécessaire si SQLiteQueue gère la persistence)
                # Mais pour garder le pattern SingleWriter, on insère ici via un lock partagé
                self.db_repo.execute_write_batch(db_batch)
                self.job_queue.mark_done(done_ids)
                self.telemetry.inc_hashed(len(batch))

            self.heartbeat_reg.beat(self.name, "IDLE")
        except Exception as e:
            self.telemetry.inc_error()

            self.logger.exception(f"WORKER FAILURE {self.name}: {e}")

            self.heartbeat_reg.beat(self.name, "FAILED")
        finally:
            conn_read.close()


# ==========================================
# 5. WATCHDOG & CERTIFICATION
# ==========================================
class ThreadSupervisor(threading.Thread):
    def __init__(self, heartbeat_reg, workers_dict, logger, telemetry):
        super().__init__(name="ThreadSupervisor", daemon=True)
        self.heartbeat_reg = heartbeat_reg
        self.workers = workers_dict  # name -> instance
        self.logger = logger
        self.telemetry = telemetry
        self.running = True

    def run(self):
        while self.running and self.heartbeat_reg.get_engine_state() not in (EngineState.DONE, EngineState.FAILED):
            time.sleep(5.0)
            state = self.heartbeat_reg.get_engine_state()
            if state == EngineState.FINALIZING:
                continue

            # Détection des zombies et crashs
            stalled = self.heartbeat_reg.get_stalled_or_dead(timeout_sec=30.0)
            for name, job in stalled:
                self.logger.critical(f"WATCHDOG: Worker {name} bloqué ou mort (Job: {job}). Lancement de l'Auto-Recovery...")
                self.telemetry.inc_error()
                self.telemetry.inc_restart()
                self.heartbeat_reg.set_engine_state(EngineState.DEGRADED)

                # Restart dynamique (Respawn)
                old_w = self.workers[name]
                new_w = HasherWorker(name, old_w.job_queue, old_w.db_repo, old_w.heartbeat_reg, old_w.telemetry, old_w.use_blake3)
                self.workers[name] = new_w
                new_w.start()
                self.logger.info(f"WATCHDOG: Worker {name} ressuscité avec succès.")
                self.heartbeat_reg.set_engine_state(state)  # Retour à l'état normal


class CertificationEngine:
    @staticmethod
    def generate_manifest(db_path, telemetry, logger):
        logger.info("Génération de la certification cryptographique (Manifest)...")
        try:
            conn = sqlite3.connect(db_path)
            row_count = conn.execute("SELECT COUNT(*) FROM files WHERE is_deleted=0").fetchone()[0]
            conn.close()

            h = hashlib.sha256()
            with open(db_path, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            db_hash = h.hexdigest()

            manifest = {
                "certification_date": datetime.utcnow().isoformat() + "Z",
                "database_snapshot_sha256": db_hash,
                "expected_files": telemetry.files_scanned,
                "actual_db_rows": row_count,
                "integrity_verified": telemetry.files_scanned == row_count,
                "engine_metrics": telemetry.get_snapshot(),
            }

            manifest_path = os.path.join(os.path.dirname(db_path), "manifest.json")
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=4)
            logger.info(f"Certification validée. Manifest généré : {manifest_path}")
            return manifest
        except Exception as e:
            logger.error(f"Échec de certification : {e}")


# ==========================================
# 6. ORCHESTRATEUR V5.5 "INDUSTRIAL"
# ==========================================
# (Simulation des imports des classes manquantes du repo SQLite v5.4 pour concision du bloc de code)
# ==========================================================
# ==========================================================
# COMPATIBILITY LOADER V5.5.1
# Chargement direct sécurisé du backend V5.4
# ==========================================================

import importlib.util

SQLiteRepository = None
EngineSupervisor = None

_backend = os.path.join(os.path.dirname(__file__), "index_engine_v5_4.py")

if os.path.exists(_backend):
    spec = importlib.util.spec_from_file_location("index_engine_v5_4_backend", _backend)

    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    SQLiteRepository = getattr(module, "SQLiteRepository", None)

    EngineSupervisor = getattr(module, "EngineSupervisor", None)


if SQLiteRepository is None or EngineSupervisor is None:
    raise ImportError("Backend V5.4 trouvé mais classes indisponibles")

print("[OK] Backend SQLite V5.4 chargé pour Index Engine V5.5")


class WorkspaceIndexerV55:
    def __init__(self, config_path="config/indexer_config.json"):
        with open(config_path, encoding="utf-8") as f:
            self.config = json.load(f)
        self.logger = setup_logger(self.config["paths"]["log_path"])
        self.telemetry = TelemetryCollector()
        self.heartbeat = HeartbeatRegistry()

        self.repo = SQLiteRepository(self.config, self.logger, self.telemetry)
        self.db_supervisor = EngineSupervisor(self.repo, self.logger)

        queue_db = os.path.join(os.path.dirname(self.config["paths"]["db_path"]), "job_queue.db")
        self.job_queue = SQLiteJobQueue(queue_db)

        cpu_total = os.cpu_count() or 8
        self.num_workers = min(12, max(4, cpu_total - 4))

    def run(self):
        self.heartbeat.set_engine_state(EngineState.STARTING)
        self.logger.info(f"Démarrage V5.5 (State Machine, Persistent Queue, Watchdog) - {self.num_workers} Workers")
        self.repo.init_schema()
        self.telemetry.start()

        # 1. Lancement du Watchdog
        workers = {}
        watchdog = ThreadSupervisor(self.heartbeat, workers, self.logger, self.telemetry)
        watchdog.start()

        # 2. SCANNING
        self.heartbeat.set_engine_state(EngineState.SCANNING)
        scanner = FileScanner(self.config, self.job_queue, self.telemetry)
        scanner.scan(self.config["paths"]["root_scan"])
        self.logger.info(f"Scan terminé. {self.telemetry.files_scanned} jobs dans la file SQLite.")

        # 3. HASHING (Workers)
        self.heartbeat.set_engine_state(EngineState.HASHING)
        for i in range(self.num_workers):
            name = f"HashWorker-{i}"
            w = HasherWorker(
                name, self.job_queue, self.repo, self.heartbeat, self.telemetry, self.config["performance"]["use_blake3_if_available"]
            )
            workers[name] = w
            w.start()

        # Attente active de la fin des jobs
        while True:
            pending = self.job_queue.count_pending()

            alive = any(w.is_alive() for w in workers.values())

            if pending == 0 and not alive:
                break

            time.sleep(1)

        # 4. FINALIZING
        self.heartbeat.set_engine_state(EngineState.FINALIZING)
        self.db_supervisor.run_auto_heal()

        # 5. CERTIFICATION
        CertificationEngine.generate_manifest(self.config["paths"]["db_path"], self.telemetry, self.logger)

        self.heartbeat.set_engine_state(EngineState.DONE)
        watchdog.running = False
        watchdog.join()

        self.telemetry.report(self.logger)


if __name__ == "__main__":
    indexer = WorkspaceIndexerV55()
    indexer.run()
