import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.storage import storage


class EvidenceStore:
    def __init__(self, db_path: str = "runtime/evidence/evidence.db"):
        self.db_path = Path(db_path)

    async def init(self) -> None:
        """Initialise la table des preuves et traces d'audit de manière idempotente."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with storage.get_connection(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evidence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    data TEXT NOT NULL,
                    task_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    async def store(self, query: str, provider: str, mode: str, data: Any, task_id: Optional[str] = None) -> int:
        """Persiste une preuve de recherche ou d'exécution."""
        data_json = json.dumps(data, ensure_ascii=False)
        with storage.get_connection(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO evidence (query, provider, mode, data, task_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (query, provider, mode, data_json, task_id),
            )
            return cursor.lastrowid

    async def get_by_task(self, task_id: str) -> List[Dict[str, Any]]:
        """Récupère toutes les preuves associées à un task_id donné."""
        with storage.get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, query, provider, mode, data, task_id, created_at
                FROM evidence
                WHERE task_id = ?
                ORDER BY id ASC
                """,
                (task_id,),
            ).fetchall()

            results = []
            for r in rows:
                try:
                    parsed_data = json.loads(r[4])
                except Exception:
                    parsed_data = r[4]
                results.append(
                    {"id": r[0], "query": r[1], "provider": r[2], "mode": r[3], "data": parsed_data, "task_id": r[5], "created_at": r[6]}
                )
            return results
