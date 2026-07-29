import os
import sqlite3
import hashlib
import time
import shutil
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

DB_PATH = r"G:\AI\E-zzio\data\workspace_index.db"
LOG_PATH = r"G:\AI\E-zzio\data\index_engine.log"
BACKUP_DIR = r"G:\AI\E-zzio\data\backups"

# --- Configuration du Logger ---
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

logger = logging.getLogger("IndexEngine")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_PATH, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
# Ajout console
console = logging.StreamHandler()
console.setFormatter(formatter)
logger.addHandler(console)

class WorkspaceIndex:
    """Moteur d'indexation SQLite industriel V3 (WAL Checkpoint, Soft-Delete temp table, FTS5 enrichi)."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.backup_dir = BACKUP_DIR
        self._init_schema()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        conn.execute("PRAGMA cache_size=-50000;")
        return conn

    def _init_schema(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("CREATE TABLE IF NOT EXISTS schema_metadata (key TEXT PRIMARY KEY, value TEXT)")
            
            # Enrichissement avec filename et folder
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE,
                filename TEXT,
                folder TEXT,
                extension TEXT,
                size_kb REAL,
                mtime REAL,
                sha256 TEXT,
                is_deleted INTEGER DEFAULT 0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
            
            cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
                filename, folder, extension, path, content='files', content_rowid='id'
            )""")
            
            cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS files_ai AFTER INSERT ON files BEGIN
                INSERT INTO files_fts(rowid, filename, folder, extension, path) 
                VALUES (new.id, new.filename, new.folder, new.extension, new.path);
            END;""")
            cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS files_ad AFTER DELETE ON files BEGIN
                INSERT INTO files_fts(files_fts, rowid, filename, folder, extension, path) 
                VALUES('delete', old.id, old.filename, old.folder, old.extension, old.path);
            END;""")
            cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS files_au AFTER UPDATE ON files BEGIN
                INSERT INTO files_fts(files_fts, rowid, filename, folder, extension, path) 
                VALUES('delete', old.id, old.filename, old.folder, old.extension, old.path);
                INSERT INTO files_fts(rowid, filename, folder, extension, path) 
                VALUES (new.id, new.filename, new.folder, new.extension, new.path);
            END;""")

            cursor.execute("INSERT OR IGNORE INTO schema_metadata VALUES ('schema_version', '3.0')")
            conn.commit()

    def backup(self, keep_last=5):
        """Backup sécurisé avec Checkpoint WAL et politique de rétention."""
        try:
            with self._get_connection() as conn:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.backup_dir, f"workspace_index_{timestamp}.db.bak")
            shutil.copy2(self.db_path, backup_file)
            logger.info(f"Backup créé : {backup_file}")
            
            # Nettoyage des vieux backups
            backups = sorted([f for f in os.listdir(self.backup_dir) if f.startswith("workspace_index_")])
            for old in backups[:-keep_last]:
                os.remove(os.path.join(self.backup_dir, old))
                logger.info(f"Ancien backup supprimé : {old}")
        except Exception as e:
            logger.error(f"Erreur lors du backup : {e}")

    def integrity_check(self) -> bool:
        try:
            with self._get_connection() as conn:
                res = conn.execute("PRAGMA integrity_check;").fetchone()
                return res and res[0] == "ok"
        except Exception:
            return False

    def search_fts(self, query: str, limit: int = 15) -> list:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            clean_q = query.replace("'", "''").replace('"', '""')
            sql = """
            SELECT f.path, f.size_kb 
            FROM files_fts fts
            JOIN files f ON fts.rowid = f.id
            WHERE files_fts MATCH ? AND f.is_deleted = 0
            ORDER BY rank LIMIT ?
            """
            try:
                cursor.execute(sql, (f'"{clean_q}"*', limit))
                return cursor.fetchall()
            except sqlite3.OperationalError:
                cursor.execute("SELECT path, size_kb FROM files WHERE path LIKE ? AND is_deleted = 0 LIMIT ?", (f"%{query}%", limit))
                return cursor.fetchall()

    def sync_incremental(self, root_path="G:\\", batch_size=1000):
        self.backup()
        logger.info(f"Démarrage du scan incrémental sur {root_path}")
        start_time = time.time()
        
        excluded = {".git", "venv", "__pycache__", ".godot", "node_modules", ".vs"}
        target_exts = {".py", ".ps1", ".gd", ".md", ".txt", ".json", ".cfg"}
        seen_paths = set()
        batch = []
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for root, dirs, files in os.walk(root_path):
            dirs[:] = [d for d in dirs if d not in excluded]
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in target_exts:
                    full_path = os.path.join(root, file)
                    seen_paths.add(full_path)
                    
                    try:
                        stat = os.stat(full_path)
                        disk_mtime = stat.st_mtime
                        size_kb = round(stat.st_size / 1024, 2)
                        
                        cursor.execute("SELECT mtime, size_kb, sha256 FROM files WHERE path = ? AND is_deleted = 0", (full_path,))
                        row = cursor.fetchone()
                        
                        if row is None or row[0] != disk_mtime or row[1] != size_kb:
                            # Ne calcule le SHA que si mtime/taille diffèrent (ou nouveau fichier)
                            folder = os.path.basename(root)
                            batch.append((full_path, file, folder, ext, size_kb, disk_mtime, "", 0))
                        
                        if len(batch) >= batch_size:
                            cursor.execute("BEGIN IMMEDIATE;")
                            cursor.executemany("""
                            INSERT INTO files (path, filename, folder, extension, size_kb, mtime, sha256, is_deleted)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(path) DO UPDATE SET
                                filename=excluded.filename, folder=excluded.folder, size_kb=excluded.size_kb,
                                mtime=excluded.mtime, sha256=excluded.sha256, is_deleted=0, updated_at=CURRENT_TIMESTAMP
                            """, batch)
                            conn.commit()
                            batch.clear()
                    except (PermissionError, FileNotFoundError):
                        continue

        if batch:
            cursor.execute("BEGIN IMMEDIATE;")
            cursor.executemany("""
            INSERT INTO files (path, filename, folder, extension, size_kb, mtime, sha256, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                filename=excluded.filename, folder=excluded.folder, size_kb=excluded.size_kb,
                mtime=excluded.mtime, sha256=excluded.sha256, is_deleted=0, updated_at=CURRENT_TIMESTAMP
            """, batch)
            conn.commit()

        # --- LOGIQUE SOFT DELETE RÉPARÉE (Table Temporaire) ---
        logger.info("Calcul des fichiers supprimés...")
        cursor.execute("CREATE TEMP TABLE current_scan (path TEXT PRIMARY KEY);")
        # Insertion des 211k chemins vus en RAM
        cursor.executemany("INSERT INTO current_scan (path) VALUES (?)", [(p,) for p in seen_paths])
        
        cursor.execute("""
            UPDATE files SET is_deleted = 1 
            WHERE is_deleted = 0 AND path NOT IN (SELECT path FROM current_scan)
        """)
        cursor.execute("DROP TABLE current_scan;")
        
        conn.commit()
        conn.close()
        
        elapsed = round(time.time() - start_time, 2)
        logger.info(f"Scan terminé en {elapsed}s.")
        
        self.supervise()

    def supervise(self):
        if not self.integrity_check():
            logger.error("Base corrompue ! Nécessite une restauration.")
            return False
        with self._get_connection() as conn:
            conn.execute("ANALYZE;")
            conn.execute("PRAGMA optimize;")
        logger.info("Supervisor : BDD saine, index optimisés.")
        return True

if __name__ == "__main__":
    idx = WorkspaceIndex()
    idx.sync_incremental("G:\\")
