import logging
from datetime import UTC, datetime

import aiosqlite

logger = logging.getLogger("ezzio.observability")


class ExecutionTracer:
    """Enregistre les traces d'exécution des inférences et routeurs dans SQLite."""

    def __init__(self, db_path: str = "runtime/evidence/evidence.db"):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS execution_traces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    latency_ms REAL NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    session_id TEXT,
                    request_id TEXT,
                    model TEXT
                );
            """)
            await db.commit()

    async def log_trace(
        self,
        provider: str,
        mode: str,
        latency_ms: float,
        status: str,
        error_message: str = None,
        session_id: str = None,
        request_id: str = None,
        model: str = None,
    ):
        try:
            await self.init()
            now = datetime.now(UTC).isoformat()
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT INTO execution_traces 
                    (timestamp, provider, mode, latency_ms, status, error_message, session_id, request_id, model) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                    (now, provider, mode, latency_ms, status, error_message, session_id, request_id, model),
                )
                await db.commit()
        except Exception as e:
            logger.error(f"[-] Erreur lors de l'enregistrement de la trace d'exécution : {e}")

    async def get_recent_traces(self, limit: int = 10):
        try:
            await self.init()
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM execution_traces ORDER BY id DESC LIMIT ?",
                    (limit,),
                )
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"[-] Erreur lors de la lecture des traces d'exécution : {e}")
            return []

