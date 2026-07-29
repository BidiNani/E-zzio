import os
import sqlite3
import hashlib
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import threading
import queue
import platform
from pathlib import Path

# --- CONFIGURATION & LOGGING ---
DB_PATH = r"G:\AI\E-zzio\data\workspace_index.db"
BACKUP_DIR = r"G:\AI\E-zzio\data\backups"
LOG_PATH = r"G:\AI\E-zzio\data\index_engine_v4.log"
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

logger = logging.getLogger("IndexEngine")
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(LOG_PATH, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
console = logging.StreamHandler()
console.setFormatter(formatter)
console.setLevel(logging.INFO)
logger.addHandler(console)

# ==========================================
# 1. METRICS REGISTRY
# ==========================================
class MetricsRegistry:
    """Télémétrie et observabilité de l'indexation."""
    def __init__(self):
        self.start_time = 0.0
        self.scan_time = 0.0
        self.hash_time = 0.0
        self.sqlite_time = 0.0
        self.files_processed = 0
        self.bytes_processed = 0
        self.new_files = 0
        self.updated_files = 0
        self.deleted_files = 0
        self.errors = 0
        self._lock = threading.Lock()

    def start(self): self.start_time = time.time()
    def add_hash_time(self, t): 
        with self._lock: self.hash_time += t
    def report(self):
        total_time = max(time.time() - self.start_time, 0.001)
        files_sec = int(self.files_processed / total_time)
        logger.info("=== METRICS REPORT ===")
        logger.info(f"Total Time : {total_time:.2f}s | Files/sec : {files_sec}")
        logger.info(f"Processed  : {self.files_processed} files | New: {self.new_files} | Updated: {self.updated_files} | Deleted: {self.deleted_files}")
        logger.info(f"Errors     : {self.errors}")
        logger.info("======================")

# ==========================================
# 2. DATABASE REPOSITORY
# ==========================================
class DatabaseRepository:
    """Gestion exclusive de la base de données et des transactions."""
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.schema_version = "4.0"

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=60.0)
        # PRAGMAs Industriels
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        conn.execute("PRAGMA mmap_size=268435456;") # 256 MB
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA locking_mode=NORMAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        conn.execute("PRAGMA page_size=4096;")
        conn.execute("PRAGMA auto_vacuum=INCREMENTAL;")
        return conn

    def init_schema(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_metadata (
                key TEXT PRIMARY KEY, value TEXT, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
            # SHA256 est maintenant un BLOB (32 octets au lieu de 64)
            # Ajout de INODE pour validation rapide
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
                sha256 BLOB,
                is_deleted INTEGER DEFAULT 0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
            
            # Index optimisés
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_folder ON files(folder);",
                "CREATE INDEX IF NOT EXISTS idx_ext_del ON files(extension, is_deleted);",
                "CREATE INDEX IF NOT EXISTS idx_file_del ON files(filename, is_deleted);",
                "CREATE INDEX IF NOT EXISTS idx_mtime ON files(mtime);",
                "CREATE INDEX IF NOT EXISTS idx_sha ON files(sha256);"
            ]
            for idx in indexes: cursor.execute(idx)

            # External Content FTS5 (Économie massive de taille DB)
            cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
                filename, folder, extension, path, content='files', content_rowid='id'
            )""")

            # Triggers FTS5
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
            cursor.execute("INSERT OR REPLACE INTO schema_metadata (key, value) VALUES ('schema_version', ?)", (self.schema_version,))
            cursor.execute("INSERT OR IGNORE INTO schema_metadata (key, value) VALUES ('created_at', CURRENT_TIMESTAMP)")
            conn.commit()

    def native_backup(self, keep_last=5):
        """Backup transactionnel natif via l'API SQLite C."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"index_{timestamp}.db.bak")
        
        try:
            with self.get_connection() as src:
                # Force WAL Checkpoint before backup
                src.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                with sqlite3.connect(backup_file) as dst:
                    src.backup(dst, pages=100, sleep=0.01)
            logger.info(f"Native Backup réussi : {backup_file}")
            
            # Rotation
            backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith("index_")])
            for old in backups[:-keep_last]:
                os.remove(os.path.join(BACKUP_DIR, old))
        except Exception as e:
            logger.error(f"Erreur de sauvegarde native : {e}")

# ==========================================
# 3. FAST SCANNER (Producer)
# ==========================================
class FileScanner:
    """Explorateur optimisé via os.scandir sans récursion bloquante."""
    def __init__(self, root_paths, metrics):
        self.root_paths = root_paths if isinstance(root_paths, list) else [root_paths]
        self.metrics = metrics
        self.excluded_dirs = {".git", "venv", "__pycache__", ".godot", "node_modules", ".vs"}
        self.target_exts = {".py", ".ps1", ".gd", ".md", ".txt", ".json", ".cfg"}

    def scan_to_queue(self, out_queue):
        """Scanne le disque et pousse les inodes/chemins dans la file d'attente."""
        dirs_to_scan = list(self.root_paths)
        
        while dirs_to_scan:
            current_dir = dirs_to_scan.pop()
            try:
                with os.scandir(current_dir) as it:
                    for entry in it:
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name not in self.excluded_dirs:
                                dirs_to_scan.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            ext = os.path.splitext(entry.name)[1].lower()
                            if ext in self.target_exts:
                                stat = entry.stat()
                                out_queue.put({
                                    "path": entry.path,
                                    "filename": entry.name,
                                    "folder": os.path.basename(current_dir),
                                    "extension": ext,
                                    "size_kb": round(stat.st_size / 1024, 2),
                                    "mtime": stat.st_mtime,
                                    "inode": stat.st_ino
                                })
                                self.metrics.files_processed += 1
                                self.metrics.bytes_processed += stat.st_size
            except (PermissionError, FileNotFoundError):
                self.metrics.errors += 1
                continue
        out_queue.put("DONE")

# ==========================================
# 4. HASH WORKERS (Consumers)
# ==========================================
class HashWorkerPool:
    """Pool de threads exploitant hashlib (libère le GIL) pour paralléliser l'analyse."""
    def __init__(self, in_queue, out_queue, db_repo, metrics, num_workers=12):
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.db_repo = db_repo
        self.metrics = metrics
        self.num_workers = num_workers
        self.db_state = {}

    def preload_state(self):
        """Charge un dictionnaire {path: (mtime, size, inode, sha256_blob)} pour validation en O(1)."""
        logger.info("Préchargement de l'état SQLite en mémoire (Cache Metadata)...")
        with self.db_repo.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT path, mtime, size_kb, inode, sha256 FROM files WHERE is_deleted=0")
            for row in cursor.fetchall():
                self.db_state[row[0]] = (row[1], row[2], row[3], row[4])

    @staticmethod
    def compute_sha256(file_path):
        h = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(65536): h.update(chunk)
            return h.digest() # Retourne un BLOB (32 bytes), pas un HEX (64 chars)
        except Exception:
            return None

    def worker_loop(self):
        while True:
            item = self.in_queue.get()
            if item == "DONE":
                self.in_queue.put("DONE")
                break
            
            path = item["path"]
            mtime, size, inode = item["mtime"], item["size_kb"], item["inode"]
            
            # Pipeline de décision de Hash (Auto-Skip)
            needs_hash = True
            cached_sha = None
            
            if path in self.db_state:
                db_mtime, db_size, db_inode, db_sha = self.db_state[path]
                if db_mtime == mtime and db_size == size and db_inode == inode:
                    needs_hash = False
                    cached_sha = db_sha
                    
            if needs_hash:
                t0 = time.time()
                sha_blob = self.compute_sha256(path)
                self.metrics.add_hash_time(time.time() - t0)
                item["sha256"] = sha_blob
                if path not in self.db_state:
                    self.metrics.new_files += 1
                else:
                    self.metrics.updated_files += 1
                self.out_queue.put(item)
            else:
                item["sha256"] = cached_sha
                self.out_queue.put(item)

    def start(self):
        self.preload_state()
        threads = []
        for _ in range(self.num_workers):
            t = threading.Thread(target=self.worker_loop)
            t.start()
            threads.append(t)
        return threads

# ==========================================
# 5. SQLITE WRITER & AUTO-HEAL SUPERVISOR
# ==========================================
class IndexSupervisor:
    """Gère l'écriture batchée, le Soft Delete optimisé et l'Auto-Heal."""
    def __init__(self, db_repo, metrics):
        self.repo = db_repo
        self.metrics = metrics

    def batch_writer(self, in_queue, total_workers):
        """Consomme la queue des workers et insère par lots transactionnels."""
        conn = self.repo.get_connection()
        cursor = conn.cursor()
        batch = []
        seen_paths_scan = set()
        done_workers = 0
        
        while done_workers < total_workers:
            try:
                item = in_queue.get(timeout=1)
                if item == "DONE":
                    done_workers += 1
                    continue
                
                seen_paths_scan.add(item["path"])
                # Ne pas réécrire en DB si c'est un fichier inchangé (évite les IOPS inutiles)
                if item["sha256"] is not None:
                    batch.append((
                        item["path"], item["filename"], item["folder"], item["extension"],
                        item["size_kb"], item["mtime"], item["inode"], item["sha256"]
                    ))
                
                if len(batch) >= 2000:
                    self._execute_batch(cursor, batch)
                    conn.commit()
                    batch.clear()
            except queue.Empty:
                pass
                
        if batch:
            self._execute_batch(cursor, batch)
            conn.commit()
            
        self._apply_soft_delete(cursor, conn, seen_paths_scan)
        conn.close()

    def _execute_batch(self, cursor, batch):
        cursor.execute("SAVEPOINT batch_save;")
        try:
            cursor.executemany("""
            INSERT INTO files (path, filename, folder, extension, size_kb, mtime, inode, sha256, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            ON CONFLICT(path) DO UPDATE SET
                filename=excluded.filename, folder=excluded.folder, size_kb=excluded.size_kb,
                mtime=excluded.mtime, inode=excluded.inode, sha256=excluded.sha256, is_deleted=0, updated_at=CURRENT_TIMESTAMP
            """, batch)
            cursor.execute("RELEASE SAVEPOINT batch_save;")
        except Exception as e:
            cursor.execute("ROLLBACK TO SAVEPOINT batch_save;")
            logger.error(f"Erreur d'insertion Batch : {e}")

    def _apply_soft_delete(self, cursor, conn, seen_paths):
        """Soft Delete utilisant une table temporaire sans saturer la RAM Python."""
        logger.info("Application du Soft Delete...")
        cursor.execute("CREATE TEMP TABLE current_scan (path TEXT PRIMARY KEY);")
        cursor.executemany("INSERT INTO current_scan (path) VALUES (?)", [(p,) for p in seen_paths])
        
        cursor.execute("""
            UPDATE files SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP
            WHERE is_deleted = 0 AND path NOT IN (SELECT path FROM current_scan)
        """)
        self.metrics.deleted_files = cursor.rowcount
        cursor.execute("DROP TABLE current_scan;")
        cursor.execute("INSERT OR REPLACE INTO schema_metadata (key, value) VALUES ('last_scan', CURRENT_TIMESTAMP)")
        conn.commit()

    def auto_heal(self, full_check=False):
        """Processus de réparation et maintenance."""
        logger.info("Lancement de l'Auto-Heal Supervisor...")
        with self.repo.get_connection() as conn:
            check_cmd = "PRAGMA integrity_check;" if full_check else "PRAGMA quick_check;"
            res = conn.execute(check_cmd).fetchone()
            if not res or res[0] != "ok":
                logger.error(f"CORRUPTION DÉTECTÉE ({res[0]}). Restauration requise !")
                # Logique de restauration à implémenter ici via le backup le plus récent
                return False
            
            logger.info("Optimisation (VACUUM INCREMENTAL, ANALYZE)...")
            conn.execute("PRAGMA incremental_vacuum;")
            conn.execute("ANALYZE;")
            conn.execute("PRAGMA optimize;")
        return True

# ==========================================
# 6. SEARCH ENGINE API
# ==========================================
class SearchEngine:
    """API de recherche riche exploitant les index optimisés et FTS5."""
    def __init__(self, db_repo):
        self.repo = db_repo

    def _run_query(self, sql, params=()):
        with self.repo.get_connection() as conn:
            return conn.cursor().execute(sql, params).fetchall()

    def search_fts(self, query: str, limit: int = 15):
        clean_q = query.replace("'", "''").replace('"', '""')
        sql = """SELECT f.path, f.size_kb FROM files_fts fts JOIN files f ON fts.rowid = f.id
                 WHERE files_fts MATCH ? AND f.is_deleted = 0 ORDER BY rank LIMIT ?"""
        return self._run_query(sql, (f'"{clean_q}"*', limit))

    def search_filename(self, filename: str, exact: bool = False):
        if exact:
            return self._run_query("SELECT path FROM files WHERE filename = ? AND is_deleted=0", (filename,))
        return self._run_query("SELECT path FROM files WHERE filename LIKE ? AND is_deleted=0", (f"%{filename}%",))

    def search_duplicates(self):
        """Trouve les fichiers avec le même hash SHA256 (Clones parfaits)."""
        sql = """SELECT hex(sha256), GROUP_CONCAT(path, ' | ') FROM files 
                 WHERE is_deleted=0 AND sha256 IS NOT NULL 
                 GROUP BY sha256 HAVING COUNT(id) > 1 LIMIT 20"""
        return self._run_query(sql)

    def search_recent(self, limit: int = 10):
        return self._run_query("SELECT path, datetime(mtime, 'unixepoch') FROM files WHERE is_deleted=0 ORDER BY mtime DESC LIMIT ?", (limit,))

# ==========================================
# 7. ORCHESTRATOR
# ==========================================
class WorkspaceIndexerV4:
    def __init__(self):
        self.metrics = MetricsRegistry()
        self.repo = DatabaseRepository()
        self.supervisor = IndexSupervisor(self.repo, self.metrics)
        self.api = SearchEngine(self.repo)
        
        self.scan_queue = queue.Queue(maxsize=20000)
        self.db_queue = queue.Queue(maxsize=20000)

    def run_full_sync(self, root_paths=["G:\\"]):
        logger.info("=== DÉMARRAGE MOTEUR V4 (Multi-thread, Streaming) ===")
        self.repo.init_schema()
        self.repo.native_backup()
        self.metrics.start()
        
        # 1. Producteur (Scan Rapide)
        scanner = FileScanner(root_paths, self.metrics)
        t_scan = threading.Thread(target=scanner.scan_to_queue, args=(self.scan_queue,))
        
        # 2. Consommateurs (Hash Workers exploitant tous les cœurs)
        num_cores = max(4, platform.processor().count("Core") if "Core" in platform.processor() else 16)
        hash_pool = HashWorkerPool(self.scan_queue, self.db_queue, self.repo, self.metrics, num_workers=num_cores)
        
        # 3. Écrivain (SQLite Batch Writer)
        t_write = threading.Thread(target=self.supervisor.batch_writer, args=(self.db_queue, num_cores))
        
        # Lancement du Pipeline
        t_scan.start()
        t_workers = hash_pool.start()
        t_write.start()
        
        # Attente de la fin
        t_scan.join()
        for t in t_workers: t.join()
        self.db_queue.put("DONE")
        t_write.join()
        
        # Post-process
        self.supervisor.auto_heal(full_check=False) # Quick check quotidien
        self.metrics.report()

if __name__ == "__main__":
    indexer = WorkspaceIndexerV4()
    indexer.run_full_sync(["G:\\AI", "G:\\Projets"]) # Remplace par G:\ entier si souhaité
    
    print("\n🔍 Test API : Recherche de doublons...")
    for h, paths in indexer.api.search_duplicates():
        print(f"Hash {h[:8]}... présent dans : {paths}")
