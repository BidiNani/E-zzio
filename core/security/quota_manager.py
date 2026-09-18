import logging
from datetime import UTC

import aiosqlite

logger = logging.getLogger("ezzio.security.quota")


class QuotaExceededError(Exception):
    """Exception levée lorsque le quota d'un fournisseur cloud est épuisé."""

    pass


class QuotaManager:
    def __init__(self, db_path: str = "runtime/evidence/evidence.db"):
        self.db_path = db_path
        self.HOURLY_LIMITS = {"gemini": 10, "tavily": 50}

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS api_usage_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );
            """)
            await db.commit()

    async def check_and_increment(self, user_id: str, provider: str) -> bool:
        try:
            await self.init()
        except Exception:
            pass

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM api_usage_ledger WHERE user_id = ? AND provider = ?;", (user_id, provider))
            count = (await cursor.fetchone())[0]
            limit = self.HOURLY_LIMITS.get(provider, 10)

            if count >= limit:
                raise QuotaExceededError(f"Quota horaire dépassé pour {provider} ({count}/{limit})")

            from datetime import datetime

            now = datetime.now(UTC).isoformat()
            await db.execute("INSERT INTO api_usage_ledger (user_id, provider, timestamp) VALUES (?, ?, ?);", (user_id, provider, now))
            await db.commit()
            return True
