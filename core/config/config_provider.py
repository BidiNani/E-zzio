import os
from typing import Any

import aiosqlite

from core.config.iconfig_provider import IConfigProvider


class ConfigProvider(IConfigProvider):
    def __init__(self, db_path: str = "runtime/config/config.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def get_config(self, key: str) -> Any | None:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = await cursor.fetchone()
            return row[0] if row else None

    async def set_config(self, key: str, value: Any) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR REPLACE INTO config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (key, str(value)))
            await db.commit()

    async def list_configs(self, prefix: str = "") -> dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT key, value FROM config WHERE key LIKE ?", (f"{prefix}%",))
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}
