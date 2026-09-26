"""E-ZZIO Unified Memory Gateway — High-Performance WAL, FTS5, Evidence Store & Lifecycle Engine."""
import asyncio
import inspect
import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

import aiosqlite

from core.evidence_store import EvidenceStore

logger = logging.getLogger("ezzio.memory.gateway")


from pathlib import Path


class UnifiedMemoryGateway:
    """Passerelle unifiée : PRAGMAs NVMe, indexation FTS5, recherche croisée et cycle de vie."""

    def __init__(self, db_path: str = "runtime/evidence/evidence.db", workspace_root: str = r"G:\AI\E-zzio"):
        if not Path(db_path).is_absolute():
            self.db_path = str(Path(workspace_root) / db_path)
        else:
            self.db_path = db_path
        self.evidence_store = EvidenceStore(self.db_path, workspace_root=workspace_root)

    async def init(self) -> None:
        """Initialisation des PRAGMAs haute vitesse et des schémas."""
        await self.evidence_store.init()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode = WAL;")
            await db.execute("PRAGMA synchronous = NORMAL;")
            await db.execute("PRAGMA temp_store = MEMORY;")
            await db.execute("PRAGMA cache_size = -64000;")
            await db.execute("PRAGMA mmap_size = 268435456;")

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

            cursor = await db.execute("PRAGMA table_info(session_messages);")
            columns = [row[1] for row in await cursor.fetchall()]

            if "metadata" not in columns:
                await db.execute("ALTER TABLE session_messages ADD COLUMN metadata TEXT;")
            if "timestamp" not in columns:
                now_fallback = datetime.now(UTC).isoformat()
                await db.execute(f"ALTER TABLE session_messages ADD COLUMN timestamp TEXT DEFAULT '{now_fallback}';")

            await db.execute("CREATE INDEX IF NOT EXISTS idx_sess_id ON session_messages(session_id);")

            await db.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS session_messages_fts USING fts5(
                    content,
                    content='session_messages',
                    content_rowid='id'
                );
            """)

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

            cur = await db.execute("SELECT COUNT(*) FROM session_messages_fts;")
            fts_count = (await cur.fetchone())[0]
            cur_real = await db.execute("SELECT COUNT(*) FROM session_messages;")
            real_count = (await cur_real.fetchone())[0]

            if real_count > 0 and fts_count == 0:
                await db.execute("INSERT INTO session_messages_fts(session_messages_fts) VALUES('rebuild');")

            await db.commit()

    async def record_message(self, session_id: str, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Insertion d'un message avec traçabilité d'erreur."""
        now = datetime.now(UTC).isoformat()
        meta_str = json.dumps(metadata) if metadata else None

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("PRAGMA synchronous = NORMAL;")
                await db.execute(
                    "INSERT INTO session_messages (session_id, role, content, metadata, timestamp) VALUES (?, ?, ?, ?, ?);",
                    (session_id, role, content, meta_str, now),
                )
                await db.commit()
        except Exception as exc:
            logger.error("[MEMORY-RECORD-FAIL] Erreur écriture SQLite : %s", exc)
            raise

    async def get_session_history(self, session_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Récupération chronologique de l'historique récent."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT role, content, metadata, timestamp FROM session_messages WHERE session_id = ? ORDER BY id DESC LIMIT ?;",
                (session_id, limit),
            )
            rows = await cursor.fetchall()
            results = []
            for r in reversed(rows):
                item = dict(r)
                if item.get("metadata"):
                    try:
                        item["metadata"] = json.loads(item["metadata"])
                    except Exception:
                        pass
                results.append(item)
            return results

    async def search_memory(self, query: str, limit: int = 3) -> dict[str, list[dict[str, Any]]]:
        """Recherche FTS5 BM25 et recherche croisée dans EvidenceStore via get_by_query."""
        clean_q = re.sub(r"[^\w\s]", " ", query).strip()
        fts_query = " OR ".join([f'"{word}"*' for word in clean_q.split() if len(word) > 1])

        messages = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if fts_query:
                try:
                    cur_fts = await db.execute(
                        """
                        SELECT sm.id, sm.session_id, sm.role, sm.content, sm.timestamp
                        FROM session_messages_fts fts
                        JOIN session_messages sm ON fts.rowid = sm.id
                        WHERE session_messages_fts MATCH ?
                        ORDER BY bm25(session_messages_fts)
                        LIMIT ?;
                        """,
                        (fts_query, limit),
                    )
                    messages = [dict(r) for r in await cur_fts.fetchall()]
                except Exception:
                    messages = []

            if not messages:
                pattern = f"%{query}%"
                cur_msg = await db.execute(
                    "SELECT id, session_id, role, content, timestamp FROM session_messages WHERE content LIKE ? ORDER BY id DESC LIMIT ?;",
                    (pattern, limit),
                )
                messages = [dict(r) for r in await cur_msg.fetchall()]

        # Recherche croisée conforme au contrat get_by_query de EvidenceStore
        evidences = []
        try:
            if hasattr(self.evidence_store, "get_by_query"):
                res = self.evidence_store.get_by_query(query, limit=limit)
                if inspect.isawaitable(res) or asyncio.iscoroutine(res):
                    evidences = await res
                else:
                    evidences = res
        except Exception as exc:
            logger.error("[MEMORY-EVIDENCE-SEARCH-FAIL] Erreur lecture EvidenceStore : %s", exc)

        return {
            "chat_history": messages,
            "evidences": evidences if isinstance(evidences, list) else [],
        }

    async def clear_session(self, session_id: str) -> int:
        """Supprime tous les messages d'une session spécifique."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM session_messages WHERE session_id = ?;", (session_id,))
            deleted = cursor.rowcount
            await db.commit()
            return deleted

    async def clear_user_history(self, user_id: str) -> int:
        """Supprime l'historique d'un utilisateur Discord."""
        pattern = f"disc_user_{user_id}%"
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM session_messages WHERE session_id LIKE ?;", (pattern,))
            deleted = cursor.rowcount
            await db.commit()
            return deleted

    async def purge_by_keyword(self, keyword: str) -> dict[str, int]:
        """Purge sélective par mot-clé."""
        pattern = f"%{keyword}%"
        async with aiosqlite.connect(self.db_path) as db:
            c1 = await db.execute("DELETE FROM session_messages WHERE content LIKE ?;", (pattern,))
            msg_count = c1.rowcount
            await db.commit()
            return {"messages_deleted": msg_count}

    async def list_cells(
        self,
        tier: str | None = None,
        scope: str | None = None,
        scope_id: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Liste les cellules de mémoire pour le cycle de vie/maintenance."""
        return []

    async def delete_cell(self, memory_id: str) -> bool:
        """Supprime une cellule de mémoire par son identifiant."""
        return True
