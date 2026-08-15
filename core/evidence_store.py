import aiosqlite
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

class EvidenceStore:
    def __init__(self, db_path: str = "runtime/evidence/evidence.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS evidence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    task_id TEXT,
                    user_id TEXT,
                    channel_id TEXT
                )
            """)
            await db.commit()
    
    async def store(self, query: str, provider: str, mode: str, data: Any, 
                    task_id: str = None, user_id: str = None, channel_id: str = None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO evidence (query, provider, mode, data, created_at, task_id, user_id, channel_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (query, provider, mode, str(data), datetime.now(timezone.utc).isoformat(), 
                 task_id, user_id, channel_id)
            )
            await db.commit()
    
    async def get_by_task(self, task_id: str) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM evidence WHERE task_id = ? ORDER BY created_at DESC",
                (task_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
