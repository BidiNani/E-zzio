import aiosqlite
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from core.evidence_store import EvidenceStore

logger = logging.getLogger("ezzio.memory.gateway")

class UnifiedMemoryGateway:
    """Passerelle unifiée de persistance mémorielle, d'audit WAL et de gestion des sessions."""

    def __init__(self, db_path: str = "runtime/evidence/evidence.db"):
        self.db_path = db_path
        self.evidence_store = EvidenceStore(db_path)

    async def init(self):
        """Initialisation de l'EvidenceStore et des tables de session en mode WAL."""
        await self.evidence_store.init()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode = WAL;")
            await db.execute("PRAGMA synchronous = NORMAL;")
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS session_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    timestamp TEXT NOT NULL
                );
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_sess_id ON session_messages(session_id);")
            await db.commit()

    async def record_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ):
        """Enregistre un message de session avec ses métadonnées d'audit (provider, intent, mode)."""
        now = datetime.now(timezone.utc).isoformat()
        meta_str = json.dumps(metadata) if metadata else None
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO session_messages (session_id, role, content, metadata, timestamp) VALUES (?, ?, ?, ?, ?);",
                (session_id, role, content, meta_str, now)
            )
            await db.commit()

    async def get_session_history(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Récupère l'historique chronologique d'une session avec désérialisation des métadonnées."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT role, content, metadata, timestamp FROM session_messages WHERE session_id = ? ORDER BY id ASC LIMIT ?;",
                (session_id, limit)
            )
            rows = await cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                if item.get("metadata"):
                    try:
                        item["metadata"] = json.loads(item["metadata"])
                    except Exception:
                        pass
                results.append(item)
            return results

    async def search_memory(self, query: str, limit: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Recherche croisée dans les preuves (evidence) et l'historique des échanges."""
        pattern = f"%{query}%"
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Recherche dans les preuves archivées
            cur_ev = await db.execute(
                "SELECT id, provider, mode, query, task_id, created_at FROM evidence WHERE query LIKE ? ORDER BY id DESC LIMIT ?;",
                (pattern, limit)
            )
            evidences = [dict(r) for r in await cur_ev.fetchall()]

            # Recherche dans les messages de session
            cur_msg = await db.execute(
                "SELECT id, session_id, role, content, metadata, timestamp FROM session_messages WHERE content LIKE ? ORDER BY id DESC LIMIT ?;",
                (pattern, limit)
            )
            messages = [dict(r) for r in await cur_msg.fetchall()]

            return {"evidences": evidences, "chat_history": messages}

    async def clear_session(self, session_id: str) -> int:
        """Supprime tous les messages d'une session donnée."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM session_messages WHERE session_id = ?;", (session_id,))
            deleted = cursor.rowcount
            await db.commit()
            return deleted

    async def clear_user_history(self, user_id: str) -> int:
        """Supprime tous les messages des sessions associées à un utilisateur Discord."""
        pattern = f"disc_user_{user_id}%"
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM session_messages WHERE session_id LIKE ?;", (pattern,))
            deleted = cursor.rowcount
            await db.commit()
            return deleted

    async def purge_by_keyword(self, keyword: str) -> Dict[str, int]:
        """Purge sélective des messages et preuves contenant un mot-clé précis."""
        pattern = f"%{keyword}%"
        async with aiosqlite.connect(self.db_path) as db:
            c1 = await db.execute("DELETE FROM session_messages WHERE content LIKE ?;", (pattern,))
            msg_count = c1.rowcount
            
            c2 = await db.execute("DELETE FROM evidence WHERE query LIKE ?;", (pattern,))
            ev_count = c2.rowcount
            
            await db.commit()
            return {"messages_deleted": msg_count, "evidences_deleted": ev_count}
