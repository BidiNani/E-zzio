import aiosqlite
import json
import logging
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from core.evidence_store import EvidenceStore

logger = logging.getLogger("ezzio.memory.gateway")

class UnifiedMemoryGateway:
    """Passerelle unifiée de persistance mémorielle, audit WAL et indexation FTS5 haute performance."""

    def __init__(self, db_path: str = "runtime/evidence/evidence.db"):
        self.db_path = db_path
        self.evidence_store = EvidenceStore(db_path)

    async def init(self):
        """Initialisation des tables relationnelles, virtuelles FTS5 et triggers."""
        await self.evidence_store.init()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode = WAL;")
            await db.execute("PRAGMA synchronous = NORMAL;")
            
            # Table relationnelle des messages
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

            # Table virtuelle FTS5 pour recherche plein texte BM25
            await db.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS session_messages_fts USING fts5(
                    content,
                    content='session_messages',
                    content_rowid='id'
                );
            """)

            # Triggers de synchronisation FTS5
            await db.execute("""
                CREATE TRIGGER IF NOT EXISTS trg_msg_insert AFTER INSERT ON session_messages BEGIN
                    INSERT INTO session_messages_fts(rowid, content) VALUES (new.id, new.content);
                END;
            """)
            await db.execute("""
                CREATE TRIGGER IF NOT EXISTS trg_msg_delete AFTER DELETE ON session_messages BEGIN
                    INSERT INTO session_messages_fts(session_messages_fts, rowid, content) VALUES('delete', old.id, old.content);
                END;
            """)

            # Synchronisation initiale de l'index FTS5 si vide
            cur = await db.execute("SELECT COUNT(*) FROM session_messages_fts;")
            fts_count = (await cur.fetchone())[0]
            cur_real = await db.execute("SELECT COUNT(*) FROM session_messages;")
            real_count = (await cur_real.fetchone())[0]

            if real_count > 0 and fts_count == 0:
                await db.execute("INSERT INTO session_messages_fts(session_messages_fts) VALUES('rebuild');")

            await db.commit()

    async def record_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ):
        now = datetime.now(timezone.utc).isoformat()
        meta_str = json.dumps(metadata) if metadata else None
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO session_messages (session_id, role, content, metadata, timestamp) VALUES (?, ?, ?, ?, ?);",
                (session_id, role, content, meta_str, now)
            )
            await db.commit()

    async def get_session_history(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
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
        """Recherche plein texte FTS5 optimisée (avec fallback LIKE pour la robustesse)."""
        clean_q = re.sub(r'[^\w\s]', ' ', query).strip()
        fts_query = " OR ".join([f'"{word}"*' for word in clean_q.split() if len(word) > 1])
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Recherche dans Evidence
            pattern = f"%{query}%"
            cur_ev = await db.execute(
                "SELECT id, provider, mode, query, task_id, created_at FROM evidence WHERE query LIKE ? ORDER BY id DESC LIMIT ?;",
                (pattern, limit)
            )
            evidences = [dict(r) for r in await cur_ev.fetchall()]

            # Recherche plein texte FTS5 sur Messages
            messages = []
            if fts_query:
                try:
                    cur_fts = await db.execute("""
                        SELECT sm.id, sm.session_id, sm.role, sm.content, sm.metadata, sm.timestamp
                        FROM session_messages_fts fts
                        JOIN session_messages sm ON fts.rowid = sm.id
                        WHERE session_messages_fts MATCH ?
                        ORDER BY bm25(session_messages_fts)
                        LIMIT ?;
                    """, (fts_query, limit))
                    messages = [dict(r) for r in await cur_fts.fetchall()]
                except Exception:
                    messages = []

            # Repli déterministe LIKE si FTS5 ne remonte rien
            if not messages:
                cur_msg = await db.execute(
                    "SELECT id, session_id, role, content, metadata, timestamp FROM session_messages WHERE content LIKE ? ORDER BY id DESC LIMIT ?;",
                    (pattern, limit)
                )
                messages = [dict(r) for r in await cur_msg.fetchall()]

            return {"evidences": evidences, "chat_history": messages}

    async def clear_session(self, session_id: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM session_messages WHERE session_id = ?;", (session_id,))
            deleted = cursor.rowcount
            await db.commit()
            return deleted

    async def clear_user_history(self, user_id: str) -> int:
        pattern = f"disc_user_{user_id}%"
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM session_messages WHERE session_id LIKE ?;", (pattern,))
            deleted = cursor.rowcount
            await db.commit()
            return deleted

    async def purge_by_keyword(self, keyword: str) -> Dict[str, int]:
        pattern = f"%{keyword}%"
        async with aiosqlite.connect(self.db_path) as db:
            c1 = await db.execute("DELETE FROM session_messages WHERE content LIKE ?;", (pattern,))
            msg_count = c1.rowcount
            c2 = await db.execute("DELETE FROM evidence WHERE query LIKE ?;", (pattern,))
            ev_count = c2.rowcount
            await db.commit()
            return {"messages_deleted": msg_count, "evidences_deleted": ev_count}
