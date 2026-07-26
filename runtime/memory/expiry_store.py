import sqlite3
from typing import List

class SQLiteExpiryStore:
    def __init__(self, db_path: str = "memory_expiry.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute('''
                CREATE TABLE IF NOT EXISTS expiry_registry (
                    memory_id TEXT PRIMARY KEY,
                    expire_at REAL NOT NULL
                )
            ''')

    def set_expiry(self, memory_id: str, expire_at: float):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO expiry_registry (memory_id, expire_at) VALUES (?, ?)", (memory_id, expire_at))

    def get_expired(self, current_time: float) -> List[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT memory_id FROM expiry_registry WHERE expire_at < ?", (current_time,))
            return [row[0] for row in cursor.fetchall()]

    def remove(self, memory_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM expiry_registry WHERE memory_id = ?", (memory_id,))
            
    def clear(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM expiry_registry")
