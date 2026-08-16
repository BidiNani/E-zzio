import aiosqlite
from typing import Any, Dict, List, Optional
from core.evidence_store import EvidenceStore

class UnifiedMemoryGateway:
    """Passerelle unifiée réconciliant preuves d'audit et mémoire conversationnelle."""

    def __init__(self, db_path: str = "runtime/evidence/evidence.db"):
        self.db_path = db_path
        self.evidence_store = EvidenceStore(db_path)

    async def init(self) -> None:
        """Initialise les tables de preuves et de sessions en mode WAL."""
        await self.evidence_store.init()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS session_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_id ON session_messages(session_id);
            """)
            await db.commit()

    async def record_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Enregistre un message dans l'historique de session."""
        async with aiosqlite.connect(self.db_path) as db:
            import json
            await db.execute(
                "INSERT INTO session_messages (session_id, role, content, metadata) VALUES (?, ?, ?, ?)",
                (session_id, role, content, json.dumps(metadata or {}))
            )
            await db.commit()

    async def get_session_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Récupère l'historique conversationnel récent d'une session."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT role, content, created_at FROM session_messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit)
            )
            rows = await cursor.fetchall()
            messages = [{"role": row["role"], "content": row["content"], "created_at": row["created_at"]} for row in rows]
            return list(reversed(messages))

    async def search_memory(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Recherche croisée dans les preuves d'audit et les messages passés."""
        evidences = await self.evidence_store.get_by_query(query, limit=limit)
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT session_id, role, content FROM session_messages WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
                (f"%{query}%", limit)
            )
            rows = await cursor.fetchall()
            chat_matches = [{"session_id": r["session_id"], "role": r["role"], "content": r["content"]} for r in rows]

        return {
            "query": query,
            "evidences": evidences,
            "chat_history": chat_matches
        }
