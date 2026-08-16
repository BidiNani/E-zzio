import json
import aiosqlite
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

class EvidenceStore:
    def __init__(self, db_path: str = "runtime/evidence/evidence.db"):
        self.db_path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS evidence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    data JSON NOT NULL,
                    task_id TEXT,
                    user_id TEXT,
                    channel_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_query ON evidence(query);")
            await db.commit()

    async def store(self, query: str, provider: str, mode: str, data: Dict[str, Any],
                    task_id: Optional[str] = None, user_id: Optional[str] = None,
                    channel_id: Optional[str] = None, created_at: Optional[str] = None) -> int:
        """Enregistre une preuve d'audit en garantissant le timestamp created_at."""
        now_ts = created_at or datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO evidence (query, provider, mode, data, task_id, user_id, channel_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (query, provider, mode, json.dumps(data), task_id, user_id, channel_id, now_ts)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_by_task(self, task_id: str) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM evidence WHERE task_id = ? ORDER BY id DESC", (task_id,))
            rows = await cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                if isinstance(item.get("data"), str):
                    try:
                        item["data"] = json.loads(item["data"])
                    except Exception:
                        pass
                results.append(item)
            return results

    async def get_by_query(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Recherche les traces d'investigation par mot-clé."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM evidence WHERE query LIKE ? ORDER BY id DESC LIMIT ?",
                (f"%{query}%", limit)
            )
            rows = await cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                if isinstance(item.get("data"), str):
                    try:
                        item["data"] = json.loads(item["data"])
                    except Exception:
                        pass
                results.append(item)
            return results
