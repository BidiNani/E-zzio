import aiosqlite
from typing import Dict, Optional

class QuotaExceededError(Exception):
    """Exception levée lors du dépassement d'un quota de requêtes."""
    pass

class QuotaManager:
    """Gestionnaire de quotas et de cadencement d'appels par utilisateur et fournisseur."""

    # Plafonds horaires par défaut
    HOURLY_LIMITS: Dict[str, int] = {
        "gemini": 60,    # 60 requêtes/heure
        "tavily": 30,    # 30 recherches/heure
        "ollama": 500,   # Local souverain (débit élevé)
    }

    def __init__(self, db_path: str = "runtime/evidence/evidence.db"):
        self.db_path = db_path

    async def init(self) -> None:
        """Initialise la table d'audit de consommation des API."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS api_usage_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    tokens_used INTEGER DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_usage_user ON api_usage_ledger(user_id, provider, timestamp);")
            await db.commit()

    async def check_and_increment(self, user_id: str, provider: str, tokens: int = 0) -> bool:
        """Vérifie le quota horaire et enregistre l'appel en cas d'autorisation."""
        limit = self.HOURLY_LIMITS.get(provider.lower(), 100)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT COUNT(*) FROM api_usage_ledger
                WHERE user_id = ? AND provider = ? AND timestamp >= datetime('now', '-1 hour')
            """, (user_id, provider.lower()))
            row = await cursor.fetchone()
            count = row[0] if row else 0

            if count >= limit:
                raise QuotaExceededError(
                    f"Quota horaire dépassé pour '{provider}' ({count}/{limit} requêtes sur 1 heure)."
                )

            await db.execute("""
                INSERT INTO api_usage_ledger (user_id, provider, tokens_used)
                VALUES (?, ?, ?)
            """, (user_id, provider.lower(), tokens))
            await db.commit()

        return True
