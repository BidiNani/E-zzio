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

HAS_BLAKE3 = False
try:
    import blake3
    HAS_BLAKE3 = True
except ImportError:
    pass

# ==========================================
# 1. JSON LOGGING
# ==========================================
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "thread": record.threadName,
            "event": record.getMessage()
        }
        if hasattr(record, "extra_data"):
            log_obj.update(record.extra_data)
        return json.dumps(log_obj, ensure_ascii=False)

def setup_logger(log_path):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logger = logging.getLogger("IndexEngineV51")
    logger.setLevel(logging.DEBUG)
    
    if not logger.handlers:
        handler = RotatingFileHandler(log_path, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s'))
        console.setLevel(logging.INFO)
        logger.addHandler(console)
    return logger

# ==========================================
# 2. TELEMETRY
# ==========================================
class TelemetryCollector:
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
            "db_deletes": self.db_deletes,
            "errors_count": self.errors,
            "retries_count": self.retries
        }
        logger.info(f"Report Final V5.1 : {speed} fichiers/sec sur {round(total_time, 2)}s", extra={"extra_data": metrics})

# ==========================================
# 3. MIGRATION & REPOSITORY
# ==========================================
class MigrationManager:
    """Gère la migration automatique des colonnes manquantes entre versions."""
    @staticmethod
    def migrate(conn, logger):
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(files)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        
        required_cols = {
            "filename": "TEXT",
            "folder": "TEXT",
            "extension": "TEXT",
            "size_kb": "REAL",
            "mtime": "REAL",
            "inode": "INTEGER",
            "hash": "BLOB",
            "is_deleted": "INTEGER DEFAULT 0",
            "updated_at": "DATETIME DEFAULT CURRENT_TIMESTAMP"
        }
        
        for col, col_type in required_cols.items():
            if col not in existing_cols:
                logger.info(f"Migration BDD : Ajout de la colonne manquante '{col}' ({col_type})...")
                cursor.execute(f"ALTER TABLE files ADD COLUMN {col} {col_type};")
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_folder ON files(folder);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ext_del ON files(extension, is_deleted);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_del ON files(filename, is_deleted);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mtime ON files(mtime);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hash ON files(hash);")
        conn.commit()

class SQLiteRepository:
    def __init__(self, config, logger, telemetry):
        self.config = config
        self.logger = logger
        self.telemetry = telemetry
        self.db_path = config["paths"]["db_path"]
        self.backup_dir = config["paths"]["backup_dir"]
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)

    def get_connection(self, read_only=False):
        p = self.config["sqlite_pragmas"]
        timeout_sec = p["busy_timeout_ms"] / 1000.0
        
        if read_only:
            # Mode lecture seule URI sécurisé
            abs_path = os.path.abspath(self.db_path).replace("\\", "/")
            db_uri = f"file:{abs_path}?mode=ro"
            conn = sqlite3.connect(db_uri, uri=True, timeout=timeout_sec)
        else:
            conn = sqlite3.connect(self.db_path, timeout=timeout_sec)
            
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        conn.execute(f"PRAGMA journal_size_limit={p['journal_size_limit_bytes']};")
        conn.execute(f"PRAGMA mmap_size={p['mmap_size_bytes']};")
        conn.execute("PRAGMA wal_autocheckpoint=1000;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def init_schema(self):
        with self.get_connection(read_only=False) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_metadata (
                key TEXT PRIMARY KEY, value TEXT, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE
            )""")
            conn.commit()
            
            # Migration dynamique du schéma
            MigrationManager.migrate(conn, self.logger)
            
            # Reconstitution de FTS5
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
            cursor.execute("INSERT OR REPLACE INTO schema_metadata (key, value) VALUES ('version', '5.1')")
            conn.commit()

    def backup_and_validate(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(self.backup_dir, f"backup_{timestamp}.db.bak")
        
        try:
            with self.get_connection(read_only=False) as src:
                src.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                with sqlite3.connect(backup_path) as dst:
                    src.backup(dst, pages=100, sleep=0.01)
                    
            with sqlite3.connect(backup_path) as test_conn:
                res = test_conn.execute("PRAGMA quick_check;").fetchone()
                if not res or res[0] != "ok":
                    os.remove(backup_path)
                    raise ValueError("Validation du backup échouée !")
            self.logger.info(f"Backup validé avec succès : {backup_path}")
        except Exception as e:
            self.logger.error(f"Échec de la sauvegarde : {e}")
            return False

        max_b = self.config["retention"]["keep_max_backups"]
        all_backups = sorted([os.path.join(self.backup_dir, f) for f in os.listdir(self.backup_dir) if f.startswith("backup_")])
        for old in all_backups[:-max_b]:
            try: os.remove(old)
            except: pass
        return True

# ==========================================
# 4. PRODUCER / CONSUMERS WORKERS
# ==========================================
class WindowsFileScanner:
    def __init__(self, config, out_queue, telemetry):
        self.config = config
        self.out_queue = out_queue
        self.telemetry = telemetry
        self.excluded_dirs = set(config["exclusions"]["dirs"])
        self.target_exts = set(config["exclusions"]["extensions"])

    def scan(self, root_paths, num_workers):
        for root_path in root_paths:
            dirs = [root_path]
            while dirs:
                curr = dirs.pop()
                try:
                    formatted_path = curr if curr.startswith("\\\\?\\") or len(curr) < 240 else "\\\\?\\" + curr
                    with os.scandir(formatted_path) as it:
                        for entry in it:
                            try:
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
                    
        # Envoi d'une sentinelle par worker
        for _ in range(num_workers):
            self.out_queue.put("SCAN_DONE")

class HasherWorker:
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
                self.out_queue.put("SCAN_DONE")
                break
            
            path = item["path"]
            mtime, size, inode = item["mtime"], item["size_kb"], item["inode"]
            
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
# 5. SINGLE WRITER ET AUTO-HEAL
# ==========================================
class SingleSQLiteWriter:
    """L'UNIQUE propriétaire de la connexion d'écriture SQLite."""
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
        
        # Connexion d'écriture UNIQUE
        conn = self.repo.get_connection(read_only=False)
        cursor = conn.cursor()
        
        cursor.execute("CREATE TEMP TABLE IF NOT EXISTS scan_session (path TEXT PRIMARY KEY);")
        conn.commit()
        
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
                    self._flush_batch(cursor, conn, batch)
                    batch.clear()
            except queue.Empty:
                pass
                
        if batch:
            self._flush_batch(cursor, conn, batch)
            
        # Soft Delete isolé dans la même transaction
        cursor.execute("SAVEPOINT soft_del_sp;")
        try:
            cursor.execute("""
                UPDATE files SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP
                WHERE is_deleted = 0 AND path NOT IN (SELECT path FROM scan_session)
            """)
            self.telemetry.db_deletes = cursor.rowcount
            cursor.execute("DROP TABLE scan_session;")
            cursor.execute("RELEASE SAVEPOINT soft_del_sp;")
            conn.commit()
        except Exception as e:
            cursor.execute("ROLLBACK TO SAVEPOINT soft_del_sp;")
            conn.commit()
            
        conn.close()

    def _flush_batch(self, cursor, conn, batch):
        for attempt in range(5):
            try:
                cursor.execute("SAVEPOINT batch_sp;")
                cursor.executemany("""
                INSERT INTO files (path, filename, folder, extension, size_kb, mtime, inode, hash, is_deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(path) DO UPDATE SET
                    filename=excluded.filename, folder=excluded.folder, size_kb=excluded.size_kb,
                    mtime=excluded.mtime, inode=excluded.inode, hash=excluded.hash, is_deleted=0, updated_at=CURRENT_TIMESTAMP
                """, batch)
                cursor.execute("RELEASE SAVEPOINT batch_sp;")
                conn.commit()
                self.telemetry.add_db_stats(len(batch), 0, 0.0)
                break
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() or "busy" in str(e).lower():
                    cursor.execute("ROLLBACK TO SAVEPOINT batch_sp;")
                    time.sleep((2 ** attempt) * 0.1 + random.uniform(0.01, 0.05))
                else:
                    cursor.execute("ROLLBACK TO SAVEPOINT batch_sp;")
                    conn.commit()
                    raise

class EngineSupervisor:
    def __init__(self, repo, logger):
        self.repo = repo
        self.logger = logger

    def run_auto_heal(self, full_integrity=False):
        self.logger.info("Auto-Heal Supervisor : Diagnostic de santé BDD...")
        with self.repo.get_connection(read_only=False) as conn:
            check_cmd = "PRAGMA integrity_check;" if full_integrity else "PRAGMA quick_check;"
            res = conn.execute(check_cmd).fetchone()
            if not res or res[0] != "ok":
                self.logger.error(f"CORRUPTION DETECTEE: {res[0]}. Restauration requise !")
                return False
            
            conn.execute("REINDEX;")
            conn.execute("INSERT INTO files_fts(files_fts) VALUES('rebuild');")
            conn.execute("PRAGMA incremental_vacuum;")
            conn.execute("ANALYZE;")
            conn.execute("PRAGMA optimize;")
        self.logger.info("Auto-Heal : BDD vérifiée, réindexée et optimisée.")
        return True

# ==========================================
# 6. SEARCH API
# ==========================================
class SearchAPI:
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

    def search_duplicates(self):
        sql = """SELECT hex(hash), GROUP_CONCAT(path, ' | ') FROM files 
                 WHERE is_deleted=0 AND hash IS NOT NULL 
                 GROUP BY hash HAVING COUNT(id) > 1 LIMIT 20"""
        return self._query(sql)

# ==========================================
# 7. ORCHESTRATEUR V5.1
# ==========================================
class WorkspaceIndexerV51:
    def __init__(self, config_path="config/indexer_config.json"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
            
        self.logger = setup_logger(self.config["paths"]["log_path"])
        self.telemetry = TelemetryCollector()
        self.repo = SQLiteRepository(self.config, self.logger, self.telemetry)
        self.supervisor = EngineSupervisor(self.repo, self.logger)
        self.search = SearchAPI(self.repo)
        
        cpu_total = os.cpu_count() or 8
        configured_workers = self.config["performance"]["num_hash_workers"]
        self.num_workers = configured_workers if configured_workers > 0 else min(32, max(4, cpu_total - 2))
        
        self.scan_queue = queue.Queue(maxsize=self.config["performance"]["queue_max_size"])
        self.write_queue = queue.Queue(maxsize=self.config["performance"]["queue_max_size"])

    def run(self):
        self.logger.info(f"Démarrage Moteur V5.1 ({self.num_workers} Hash Workers, BLAKE3={HAS_BLAKE3})")
        self.repo.init_schema()
        self.repo.backup_and_validate()
        self.telemetry.start()

        # 1. Thread Scanner
        scanner = WindowsFileScanner(self.config, self.scan_queue, self.telemetry)
        t_scanner = threading.Thread(target=scanner.scan, args=(self.config["paths"]["root_scan"], self.num_workers), name="ScannerThread")

        # 2. Hash Worker Threads
        worker_threads = []
        conn_reads = [self.repo.get_connection(read_only=True) for _ in range(self.num_workers)]
        
        for i in range(self.num_workers):
            hw = HasherWorker(self.scan_queue, self.write_queue, self.repo, self.telemetry, self.config["performance"]["use_blake3_if_available"])
            t = threading.Thread(target=hw.run, args=(conn_reads[i],), name=f"HashWorker-{i}")
            worker_threads.append(t)

        # 3. Thread SQLite Writer Unique
        writer = SingleSQLiteWriter(self.write_queue, self.repo, self.config, self.telemetry, self.num_workers)
        t_writer = threading.Thread(target=writer.run_writer_loop, name="SQLiteWriterThread")

        t_scanner.start()
        for t in worker_threads: t.start()
        t_writer.start()

        t_scanner.join()
        for t in worker_threads: t.join()
        t_writer.join()

        for c in conn_reads: c.close()

        self.supervisor.run_auto_heal(full_integrity=False)
        self.telemetry.report(self.logger)

if __name__ == "__main__":
    indexer = WorkspaceIndexerV51()
    indexer.run()
