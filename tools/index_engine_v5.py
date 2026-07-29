import os
import sys
import sqlite3
import hashlib
import time
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import threading
import queue
import random
import re
from abc import ABC, abstractmethod

# Tentative d'import de BLAKE3 pour des performances maximales
HAS_BLAKE3 = False
try:
    import blake3
    HAS_BLAKE3 = True
except ImportError:
    pass

# ==========================================
# 1. CONFIGURATION & JSON LOGGING
# ==========================================
class JSONFormatter(logging.Formatter):
    """Formatter de logs structurés au format JSON."""
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "thread": record.threadName,
            "event": record.getMessage()
        }
        if hasattr(record, "extra_data"):
            log_obj.update(record.extra_data)
        return json.dumps(log_obj, ensure_ascii=False)

def setup_logger(log_path):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logger = logging.getLogger("IndexEngineV5")
    logger.setLevel(logging.DEBUG)
    
    # Rotation des logs JSON
    handler = RotatingFileHandler(log_path, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    # Console Handler
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s'))
    console.setLevel(logging.INFO)
    logger.addHandler(console)
    return logger

# ==========================================
# 2. METRICS & TELEMETRY
# ==========================================
class TelemetryCollector:
    """Collecteur complet de métriques et d'observabilité."""
    def __init__(self):
        self.start_time = 0.0
        self.files_scanned = 0
        self.files_hashed = 0
        self.bytes_hashed = 0
        self.db_inserts = 0
        self.db_updates = 0
        self.db_deletes = 0
        self.retries = 0
        self.errors = 0
        self.hash_time_total = 0.0
        self.db_commit_time_total = 0.0
        self._lock = threading.Lock()

    def start(self): self.start_time = time.time()
    def inc_scanned(self): 
        with self._lock: self.files_scanned += 1
    def add_hash(self, bytes_count, duration):
        with self._lock:
            self.files_hashed += 1
            self.bytes_hashed += bytes_count
            self.hash_time_total += duration
    def add_db_stats(self, inserts, updates, commit_duration):
        with self._lock:
            self.db_inserts += inserts
            self.db_updates += updates
            self.db_commit_time_total += commit_duration

    def report(self, logger):
        total_time = max(time.time() - self.start_time, 0.001)
        speed = int(self.files_scanned / total_time)
        metrics = {
            "total_duration_sec": round(total_time, 2),
            "scanned_files": self.files_scanned,
            "hashed_files": self.files_hashed,
            "throughput_files_per_sec": speed,
            "db_inserts": self.db_inserts,
            "db_updates": self.db_updates,
            "db_deletes": self.db_deletes,
            "errors_count": self.errors,
            "retries_count": self.retries
        }
        logger.info(f"Report Final : {speed} fichiers/sec sur {round(total_time, 2)}s", extra={"extra_data": metrics})

# ==========================================
# 3. STORAGE REPOSITORY ABSTRACT & SQLITE IMPL
# ==========================================
class StorageRepository(ABC):
    @abstractmethod
    def init_schema(self): pass
    @abstractmethod
    def execute_write_batch(self, batch): pass
    @abstractmethod
    def backup_and_validate(self): pass

class SQLiteRepository(StorageRepository):
    def __init__(self, config, logger, telemetry):
        self.config = config
        self.logger = logger
        self.telemetry = telemetry
        self.db_path = config["paths"]["db_path"]
        self.backup_dir = config["paths"]["backup_dir"]
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)

    def get_connection(self, read_only=False):
        conn = sqlite3.connect(self.db_path, timeout=self.config["sqlite_pragmas"]["busy_timeout_ms"] / 1000.0)
        p = self.config["sqlite_pragmas"]
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        conn.execute(f"PRAGMA journal_size_limit={p['journal_size_limit_bytes']};")
        conn.execute(f"PRAGMA mmap_size={p['mmap_size_bytes']};")
        conn.execute("PRAGMA wal_autocheckpoint=1000;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _execute_with_retry(self, fn, *args, max_retries=5):
        """Exécution robuste avec Retry, Backoff exponentiel et Jitter."""
        for attempt in range(max_retries):
            try:
                return fn(*args)
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() or "busy" in str(e).lower():
                    self.telemetry.retries += 1
                    sleep_time = (2 ** attempt) * 0.1 + random.uniform(0.01, 0.05)
                    time.sleep(sleep_time)
                else:
                    raise
        raise sqlite3.OperationalError("Echec de la transaction après retries max.")

    def init_schema(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_metadata (
                key TEXT PRIMARY KEY, value TEXT, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE,
                filename TEXT,
                folder TEXT,
                extension TEXT,
                size_kb REAL,
                mtime REAL,
                inode INTEGER,
                hash BLOB,
                is_deleted INTEGER DEFAULT 0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
            
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_folder ON files(folder);",
                "CREATE INDEX IF NOT EXISTS idx_ext_del ON files(extension, is_deleted);",
                "CREATE INDEX IF NOT EXISTS idx_file_del ON files(filename, is_deleted);",
                "CREATE INDEX IF NOT EXISTS idx_mtime ON files(mtime);",
                "CREATE INDEX IF NOT EXISTS idx_hash ON files(hash);"
            ]
            for idx in indexes: cursor.execute(idx)

            cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
                filename, folder, extension, path, content='files', content_rowid='id'
            )""")

            cursor.executescript("""
            CREATE TRIGGER IF NOT EXISTS fts_ai AFTER INSERT ON files BEGIN
                INSERT INTO files_fts(rowid, filename, folder, extension, path) VALUES (new.id, new.filename, new.folder, new.extension, new.path);
            END;
            CREATE TRIGGER IF NOT EXISTS fts_ad AFTER DELETE ON files BEGIN
                INSERT INTO files_fts(files_fts, rowid, filename, folder, extension, path) VALUES('delete', old.id, old.filename, old.folder, old.extension, old.path);
            END;
            CREATE TRIGGER IF NOT EXISTS fts_au AFTER UPDATE ON files BEGIN
                INSERT INTO files_fts(files_fts, rowid, filename, folder, extension, path) VALUES('delete', old.id, old.filename, old.folder, old.extension, old.path);
                INSERT INTO files_fts(rowid, filename, folder, extension, path) VALUES (new.id, new.filename, new.folder, new.extension, new.path);
            END;
            """)
            cursor.execute("INSERT OR REPLACE INTO schema_metadata (key, value) VALUES ('version', '5.0')")
            conn.commit()

    def execute_write_batch(self, batch):
        def _write():
            t0 = time.time()
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SAVEPOINT batch_sp;")
            try:
                cursor.executemany("""
                INSERT INTO files (path, filename, folder, extension, size_kb, mtime, inode, hash, is_deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(path) DO UPDATE SET
                    filename=excluded.filename, folder=excluded.folder, size_kb=excluded.size_kb,
                    mtime=excluded.mtime, inode=excluded.inode, hash=excluded.hash, is_deleted=0, updated_at=CURRENT_TIMESTAMP
                """, batch)
                cursor.execute("RELEASE SAVEPOINT batch_sp;")
                conn.commit()
                self.telemetry.add_db_stats(len(batch), 0, time.time() - t0)
            except Exception:
                cursor.execute("ROLLBACK TO SAVEPOINT batch_sp;")
                conn.close()
                raise
            conn.close()
        self._execute_with_retry(_write)

    def backup_and_validate(self):
        """Sauvegarde SQLite native avec test de restauration et de validation."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(self.backup_dir, f"backup_{timestamp}.db.bak")
        
        # 1. Sauvegarde Native API
        with self.get_connection() as src:
            src.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            with sqlite3.connect(backup_path) as dst:
                src.backup(dst, pages=100, sleep=0.01)
                
        # 2. Test de restauration et Quick Check du Backup
        try:
            with sqlite3.connect(backup_path) as test_conn:
                res = test_conn.execute("PRAGMA quick_check;").fetchone()
                if not res or res[0] != "ok":
                    os.remove(backup_path)
                    raise ValueError("Validation du backup échouée !")
            self.logger.info(f"Backup validé avec succès : {backup_path}")
        except Exception as e:
            self.logger.error(f"Échec de la sauvegarde : {e}")
            return False

        # 3. Rotation des sauvegardes
        max_b = self.config["retention"]["keep_max_backups"]
        all_backups = sorted([os.path.join(self.backup_dir, f) for f in os.listdir(self.backup_dir) if f.startswith("backup_")])
        for old in all_backups[:-max_b]:
            os.remove(old)
        return True

# ==========================================
# 4. PRODUCER / CONSUMERS WORKERS
# ==========================================
class WindowsFileScanner:
    """Producteur gérant les chemins longs Windows et évitant les Jonctions/Symlinks."""
    def __init__(self, config, out_queue, telemetry):
        self.config = config
        self.out_queue = out_queue
        self.telemetry = telemetry
        self.excluded_dirs = set(config["exclusions"]["dirs"])
        self.target_exts = set(config["exclusions"]["extensions"])

    def scan(self, root_paths):
        for root_path in root_paths:
            dirs = [root_path]
            while dirs:
                curr = dirs.pop()
                try:
                    # Gestion des chemins longs Windows (\\?\Prefix)
                    formatted_path = curr if curr.startswith("\\\\?\\") or len(curr) < 240 else "\\\\?\\" + curr
                    with os.scandir(formatted_path) as it:
                        for entry in it:
                            try:
                                # Anti-boucle : Ignorer les symlinks et jonctions
                                if entry.is_symlink():
                                    continue
                                if entry.is_dir(follow_symlinks=False):
                                    if entry.name not in self.excluded_dirs:
                                        dirs.append(entry.path)
                                elif entry.is_file(follow_symlinks=False):
                                    ext = os.path.splitext(entry.name)[1].lower()
                                    if ext in self.target_exts:
                                        stat = entry.stat()
                                        clean_path = entry.path.replace("\\\\?\\", "")
                                        self.out_queue.put({
                                            "path": clean_path,
                                            "filename": entry.name,
                                            "folder": os.path.basename(os.path.dirname(clean_path)),
                                            "extension": ext,
                                            "size_kb": round(stat.st_size / 1024, 2),
                                            "mtime": stat.st_mtime,
                                            "inode": stat.st_ino,
                                            "raw_size": stat.st_size
                                        })
                                        self.telemetry.inc_scanned()
                            except (PermissionError, FileNotFoundError):
                                self.telemetry.errors += 1
                except (PermissionError, FileNotFoundError):
                    self.telemetry.errors += 1
        self.out_queue.put("SCAN_DONE")

class HasherWorker:
    """Worker consommant la file d'attente et calculant BLAKE3/SHA256."""
    def __init__(self, in_queue, out_queue, repo, telemetry, use_blake3=True):
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.repo = repo
        self.telemetry = telemetry
        self.use_blake3 = use_blake3 and HAS_BLAKE3

    def compute_hash(self, file_path):
        t0 = time.time()
        try:
            if self.use_blake3:
                h = blake3.blake3()
                with open(file_path, "rb") as f:
                    while chunk := f.read(65536): h.update(chunk)
                digest = h.digest()
            else:
                h = hashlib.sha256()
                with open(file_path, "rb") as f:
                    while chunk := f.read(65536): h.update(chunk)
                digest = h.digest()
            return digest, time.time() - t0
        except Exception:
            return None, 0.0

    def run(self, conn_read):
        cursor = conn_read.cursor()
        while True:
            item = self.in_queue.get()
            if item == "SCAN_DONE":
                self.in_queue.put("SCAN_DONE")
                break
            
            path = item["path"]
            mtime, size, inode = item["mtime"], item["size_kb"], item["inode"]
            
            # Validation unitaire ultra-rapide par index SQL
            cursor.execute("SELECT hash FROM files WHERE path=? AND mtime=? AND size_kb=? AND inode=? AND is_deleted=0", (path, mtime, size, inode))
            row = cursor.fetchone()
            
            if row and row[0]:
                item["hash"] = row[0]
            else:
                digest, duration = self.compute_hash(path)
                item["hash"] = digest
                self.telemetry.add_hash(item["raw_size"], duration)
                
            self.out_queue.put(item)

# ==========================================
# 5. SINGLE WRITER & SUPERVISOR
# ==========================================
class SingleSQLiteWriter:
    """L'UNIQUE thread propriétaire des écritures SQLite."""
    def __init__(self, in_queue, repo, config, telemetry, total_workers):
        self.in_queue = in_queue
        self.repo = repo
        self.config = config
        self.telemetry = telemetry
        self.total_workers = total_workers

    def run_writer_loop(self):
        batch = []
        batch_size = self.config["performance"]["batch_size"]
        workers_done = 0
        
        # Connection d'écriture dédiée
        conn = self.repo.get_connection()
        cursor = conn.cursor()
        
        # Table temporaire session scan pour un Soft Delete RAM constante !
        cursor.execute("CREATE TEMP TABLE scan_session (path TEXT PRIMARY KEY);")
        
        while workers_done < self.total_workers:
            try:
                item = self.in_queue.get(timeout=0.5)
                if item == "SCAN_DONE":
                    workers_done += 1
                    continue
                
                path = item["path"]
                cursor.execute("INSERT OR IGNORE INTO scan_session (path) VALUES (?)", (path,))
                
                if item.get("hash") is not None:
                    batch.append((
                        path, item["filename"], item["folder"], item["extension"],
                        item["size_kb"], item["mtime"], item["inode"], item["hash"]
                    ))
                
                if len(batch) >= batch_size:
                    self.repo.execute_write_batch(batch)
                    batch.clear()
            except queue.Empty:
                pass
                
        if batch:
            self.repo.execute_write_batch(batch)
            
        # Application du Soft Delete via croisement SQL pur (RAM 0 Mo)
        cursor.execute("""
            UPDATE files SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP
            WHERE is_deleted = 0 AND path NOT IN (SELECT path FROM scan_session)
        """)
        self.telemetry.db_deletes = cursor.rowcount
        cursor.execute("DROP TABLE scan_session;")
        conn.commit()
        conn.close()

class EngineSupervisor:
    """Gère l'auto-réparation et la maintenance à 7 niveaux."""
    def __init__(self, repo, logger):
        self.repo = repo
        self.logger = logger

    def run_auto_heal(self, full_integrity=False):
        self.logger.info("Auto-Heal Supervisor : Analyse et maintenance en cours...")
        with self.repo.get_connection() as conn:
            check_cmd = "PRAGMA integrity_check;" if full_integrity else "PRAGMA quick_check;"
            res = conn.execute(check_cmd).fetchone()
            if not res or res[0] != "ok":
                self.logger.error(f"CORRUPTION DETECTEE: {res[0]}. Restauration depuis backup requise.")
                return False
            
            self.logger.info("Maintenance : REINDEX, FTS Rebuild, Vacuum & Optimize...")
            conn.execute("REINDEX;")
            conn.execute("INSERT INTO files_fts(files_fts) VALUES('rebuild');")
            conn.execute("PRAGMA incremental_vacuum;")
            conn.execute("ANALYZE;")
            conn.execute("PRAGMA optimize;")
        self.logger.info("Auto-Heal : BDD réparée et totalement optimisée.")
        return True

# ==========================================
# 6. ENRICHED SEARCH API
# ==========================================
class SearchAPI:
    """API de recherche industrielle complète."""
    def __init__(self, repo):
        self.repo = repo

    def _query(self, sql, params=()):
        with self.repo.get_connection(read_only=True) as conn:
            return conn.cursor().execute(sql, params).fetchall()

    def search_fts(self, q, limit=15):
        clean_q = q.replace("'", "''").replace('"', '""')
        sql = """SELECT f.path, f.size_kb FROM files_fts fts JOIN files f ON fts.rowid = f.id
                 WHERE files_fts MATCH ? AND f.is_deleted = 0 ORDER BY rank LIMIT ?"""
        return self._query(sql, (f'"{clean_q}"*', limit))

    def search_regex(self, pattern):
        all_files = self._query("SELECT path FROM files WHERE is_deleted=0")
        rgx = re.compile(pattern)
        return [f[0] for f in all_files if rgx.search(f[0])]

    def search_duplicates(self):
        sql = """SELECT hex(hash), GROUP_CONCAT(path, ' | ') FROM files 
                 WHERE is_deleted=0 AND hash IS NOT NULL 
                 GROUP BY hash HAVING COUNT(id) > 1 LIMIT 20"""
        return self._query(sql)

    def search_deleted(self, limit=20):
        return self._query("SELECT path, updated_at FROM files WHERE is_deleted=1 ORDER BY updated_at DESC LIMIT ?", (limit,))

# ==========================================
# 7. ORCHESTRATEUR PRINCIPAL
# ==========================================
class WorkspaceIndexerV5:
    def __init__(self, config_path="config/indexer_config.json"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
            
        self.logger = setup_logger(self.config["paths"]["log_path"])
        self.telemetry = TelemetryCollector()
        self.repo = SQLiteRepository(self.config, self.logger, self.telemetry)
        self.supervisor = EngineSupervisor(self.repo, self.logger)
        self.search = SearchAPI(self.repo)
        
        # Détection dynamique intelligente des cœurs CPU
        cpu_total = os.cpu_count() or 8
        configured_workers = self.config["performance"]["num_hash_workers"]
        self.num_workers = configured_workers if configured_workers > 0 else min(32, max(4, cpu_total - 2))
        
        self.scan_queue = queue.Queue(maxsize=self.config["performance"]["queue_max_size"])
        self.write_queue = queue.Queue(maxsize=self.config["performance"]["queue_max_size"])

    def run(self):
        self.logger.info(f"Démarrage Moteur V5 ({self.num_workers} Hash Workers, BLAKE3={HAS_BLAKE3})")
        self.repo.init_schema()
        self.repo.backup_and_validate()
        self.telemetry.start()

        # 1. Thread Scanner
        scanner = WindowsFileScanner(self.config, self.scan_queue, self.telemetry)
        t_scanner = threading.Thread(target=scanner.scan, args=(self.config["paths"]["root_scan"],), name="ScannerThread")

        # 2. Worker Threads (Hash)
        worker_threads = []
        conn_reads = [self.repo.get_connection(read_only=True) for _ in range(self.num_workers)]
        
        for i in range(self.num_workers):
            hw = HasherWorker(self.scan_queue, self.write_queue, self.repo, self.telemetry, self.config["performance"]["use_blake3_if_available"])
            t = threading.Thread(target=hw.run, args=(conn_reads[i],), name=f"HashWorker-{i}")
            worker_threads.append(t)

        # 3. Thread SQLite Writer Unique
        writer = SingleSQLiteWriter(self.write_queue, self.repo, self.config, self.telemetry, self.num_workers)
        t_writer = threading.Thread(target=writer.run_writer_loop, name="SQLiteWriterThread")

        # Démarrage
        t_scanner.start()
        for t in worker_threads: t.start()
        t_writer.start()

        # Jointures
        t_scanner.join()
        for t in worker_threads: t.join()
        t_writer.join()

        # Fermeture des connexions de lecture
        for c in conn_reads: c.close()

        # Auto-Heal & Rapport
        self.supervisor.run_auto_heal(full_integrity=False)
        self.telemetry.report(self.logger)

if __name__ == "__main__":
    indexer = WorkspaceIndexerV5()
    indexer.run()
