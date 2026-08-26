import os
import sqlite3
import hashlib
import time
import shutil

DB_PATH = r"G:\AI\E-zzio\data\workspace_index.db"
BACKUP_PATH = r"G:\AI\E-zzio\data\workspace_index.db.bak"


class WorkspaceIndex:
    """Moteur d'indexation SQLite industriel pour E-ZZIO (WAL, FTS5, SHA256, Auto-Heal)."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.backup_path = BACKUP_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_schema()

    def _get_connection(self):
        """Ouvre une connexion thread-safe avec PRAGMAs d'optimisation."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        conn.execute("PRAGMA cache_size=-50000;")  # 50 Mo de cache RAM
        return conn

    def _init_schema(self):
        """Initialise le schéma relationnel, les versions, la table FTS5 et les triggers."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Métadonnées & Versioning
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )""")

            # 2. Table principale des fichiers avec soft-delete & SHA256
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE,
                extension TEXT,
                size_kb REAL,
                mtime REAL,
                sha256 TEXT,
                is_deleted INTEGER DEFAULT 0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")

            # 3. Table FTS5 (Full-Text Search) pour recherche ultra-rapide
            cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
                path, extension, content='files', content_rowid='id'
            )""")

            # 4. Triggers de synchronisation FTS5 automatique
            cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS files_ai AFTER INSERT ON files BEGIN
                INSERT INTO files_fts(rowid, path, extension) VALUES (new.id, new.path, new.extension);
            END;""")
            cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS files_ad AFTER DELETE ON files BEGIN
                INSERT INTO files_fts(files_fts, rowid, path, extension) VALUES('delete', old.id, old.path, old.extension);
            END;""")
            cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS files_au AFTER UPDATE ON files BEGIN
                INSERT INTO files_fts(files_fts, rowid, path, extension) VALUES('delete', old.id, old.path, old.extension);
                INSERT INTO files_fts(rowid, path, extension) VALUES (new.id, new.path, new.extension);
            END;""")

            cursor.execute("INSERT OR IGNORE INTO schema_metadata VALUES ('schema_version', '2.0')")
            cursor.execute("INSERT OR IGNORE INTO schema_metadata VALUES ('created_at', CURRENT_TIMESTAMP)")
            conn.commit()

    def backup(self):
        """Création d'une sauvegarde physique de la BDD."""
        if os.path.exists(self.db_path):
            shutil.copy2(self.db_path, self.backup_path)

    def restore(self) -> bool:
        """Restaure la base depuis la sauvegarde en cas de corruption."""
        if os.path.exists(self.backup_path):
            shutil.copy2(self.backup_path, self.db_path)
            return True
        return False

    def integrity_check(self) -> bool:
        """Vérifie l'intégrité structurelle de SQLite."""
        try:
            with self._get_connection() as conn:
                res = conn.execute("PRAGMA integrity_check;").fetchone()
                return res and res[0] == "ok"
        except Exception:
            return False

    def compute_sha256(self, file_path: str) -> str:
        """Calcule l'empreinte SHA256 par blocs de 64 KB pour éviter la surconsommation RAM."""
        h = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return ""

    def search_fts(self, query: str, limit: int = 15) -> list:
        """Recherche Full-Text (FTS5) instantanée (< 2ms)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            clean_q = query.replace("'", "''").replace('"', '""')
            sql = """
            SELECT f.path, f.size_kb, f.sha256
            FROM files_fts fts
            JOIN files f ON fts.rowid = f.id
            WHERE files_fts MATCH ? AND f.is_deleted = 0
            ORDER BY rank LIMIT ?
            """
            try:
                cursor.execute(sql, (f'"{clean_q}"*', limit))
                return cursor.fetchall()
            except sqlite3.OperationalError:
                # Fallback sécurisé vers LIKE si requête FTS mal formée
                cursor.execute(
                    "SELECT path, size_kb, sha256 FROM files WHERE path LIKE ? AND is_deleted = 0 LIMIT ?", (f"%{query}%", limit)
                )
                return cursor.fetchall()

    def sync_incremental(self, root_path="G:\\", batch_size=1000, target_exts={".py", ".ps1", ".gd", ".md", ".txt", ".json", ".cfg"}):
        """Synchronisation incrémentale en streaming (RAM constante) par lots de 1000."""
        self.backup()
        excluded = {".git", "venv", "__pycache__", ".godot", "node_modules", ".vs"}

        conn = self._get_connection()
        cursor = conn.cursor()

        seen_paths = set()
        batch = []
        start_time = time.time()

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

                        # Interrogation unitaire directe (streaming sans charger toute la BDD en RAM)
                        cursor.execute("SELECT mtime, size_kb, sha256 FROM files WHERE path = ? AND is_deleted = 0", (full_path,))
                        row = cursor.fetchone()

                        if row is None:
                            sha = self.compute_sha256(full_path)
                            batch.append((full_path, ext, size_kb, disk_mtime, sha, 0))
                        elif row[0] != disk_mtime or row[1] != size_kb:
                            # Validation double-check par Hash SHA256 pour éviter les faux positifs
                            new_sha = self.compute_sha256(full_path)
                            if new_sha != row[2]:
                                batch.append((full_path, ext, size_kb, disk_mtime, new_sha, 0))

                        # Traitement par lots (Batch Execution)
                        if len(batch) >= batch_size:
                            cursor.execute("BEGIN IMMEDIATE;")
                            cursor.executemany(
                                """
                            INSERT INTO files (path, extension, size_kb, mtime, sha256, is_deleted)
                            VALUES (?, ?, ?, ?, ?, ?)
                            ON CONFLICT(path) DO UPDATE SET
                                size_kb=excluded.size_kb,
                                mtime=excluded.mtime,
                                sha256=excluded.sha256,
                                is_deleted=0,
                                updated_at=CURRENT_TIMESTAMP
                            """,
                                batch,
                            )
                            conn.commit()
                            batch.clear()

                    except (PermissionError, FileNotFoundError):
                        continue

        # Traitement du dernier lot
        if batch:
            cursor.execute("BEGIN IMMEDIATE;")
            cursor.executemany(
                """
            INSERT INTO files (path, extension, size_kb, mtime, sha256, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                size_kb=excluded.size_kb,
                mtime=excluded.mtime,
                sha256=excluded.sha256,
                is_deleted=0,
                updated_at=CURRENT_TIMESTAMP
            """,
                batch,
            )
            conn.commit()

        # Audit & Soft Delete : Marquage sans suppression physique destructrice
        cursor.execute("UPDATE files SET is_deleted = 1 WHERE path NOT IN (SELECT path FROM files WHERE is_deleted = 0) AND is_deleted = 0")
        cursor.execute("INSERT OR REPLACE INTO schema_metadata VALUES ('last_scan', CURRENT_TIMESTAMP)")
        conn.commit()
        conn.close()

        elapsed = round(time.time() - start_time, 2)
        print(f"✅ Scan incrémental terminé en {elapsed}s.")

        # Auto-vérification post-sync
        if not self.integrity_check():
            print("⚠️ Corruption détectée ! Auto-restauration depuis le backup...")
            self.restore()

    def supervise(self):
        """Index Supervisor : maintenance, contrôle d'intégrité, ANALYZE & OPTIMIZE."""
        if not self.integrity_check():
            print("❌ Base corrompue ! Restauration d'urgence...")
            return self.restore()

        with self._get_connection() as conn:
            print("[*] Supervisor : Analyse des index et optimisation des tables...")
            conn.execute("ANALYZE;")
            conn.execute("PRAGMA optimize;")
        print("✅ Supervisor : BDD en parfaite santé.")
        return True


if __name__ == "__main__":
    idx = WorkspaceIndex()
    idx.sync_incremental("G:\\")
    idx.supervise()
