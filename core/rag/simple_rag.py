import aiosqlite
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ezzio.rag")


class SimpleRAG:
    """Moteur RAG souverain avec indexation plein texte FTS5 et scoring BM25."""

    def __init__(self, db_path: str = "runtime/rag/documents.db"):
        self.db_path = db_path
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    async def init(self):
        """Initialise la table principale et la table virtuelle FTS5 avec triggers de synchronisation."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode = WAL;")
            await db.execute("PRAGMA synchronous = NORMAL;")

            # 1. Table principale de stockage
            await db.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    tag TEXT DEFAULT 'general',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Migration douce si tag manquant
            cursor = await db.execute("PRAGMA table_info(documents);")
            cols = [row[1] for row in await cursor.fetchall()]
            if "tag" not in cols:
                await db.execute("ALTER TABLE documents ADD COLUMN tag TEXT DEFAULT 'general';")

            await db.execute("CREATE INDEX IF NOT EXISTS idx_documents_tag ON documents(tag);")

            # 2. Table virtuelle FTS5
            await db.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                    content,
                    tag UNINDEXED,
                    content='documents',
                    content_rowid='id'
                );
            """)

            # 3. Triggers de synchronisation automatique FTS5
            await db.execute("""
                CREATE TRIGGER IF NOT EXISTS trg_docs_ai AFTER INSERT ON documents BEGIN
                    INSERT INTO documents_fts(rowid, content, tag) VALUES (new.id, new.content, new.tag);
                END;
            """)
            await db.execute("""
                CREATE TRIGGER IF NOT EXISTS trg_docs_ad AFTER DELETE ON documents BEGIN
                    INSERT INTO documents_fts(documents_fts, rowid, content, tag) VALUES('delete', old.id, old.content, old.tag);
                END;
            """)
            await db.execute("""
                CREATE TRIGGER IF NOT EXISTS trg_docs_au AFTER UPDATE ON documents BEGIN
                    INSERT INTO documents_fts(documents_fts, rowid, content, tag) VALUES('delete', old.id, old.content, old.tag);
                    INSERT INTO documents_fts(rowid, content, tag) VALUES (new.id, new.content, new.tag);
                END;
            """)

            await db.commit()
            logger.info("[RAG] Base de connaissances FTS5 initialisée : %s", self.db_path)

    async def add_document(self, content: str, metadata: Optional[Dict[str, Any]] = None, tag: str = "general") -> int:
        """Ajoute un document à la base de connaissances."""
        meta_str = json.dumps(metadata) if metadata else None
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO documents (content, metadata, tag) VALUES (?, ?, ?);",
                (content, meta_str, tag),
            )
            await db.commit()
            return cursor.lastrowid

    async def add_documents(self, docs: List[Dict[str, Any]]) -> List[int]:
        """Insertion par lot pour de hautes performances."""
        ids = []
        async with aiosqlite.connect(self.db_path) as db:
            for doc in docs:
                content = doc.get("content", "")
                metadata = doc.get("metadata")
                tag = doc.get("tag", "general")
                meta_str = json.dumps(metadata) if metadata else None
                cursor = await db.execute(
                    "INSERT INTO documents (content, metadata, tag) VALUES (?, ?, ?);",
                    (content, meta_str, tag),
                )
                ids.append(cursor.lastrowid)
            await db.commit()
        return ids

    async def search_documents(self, query: str, limit: int = 5, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """Recherche plein texte par pertinence BM25 avec fallback si pas de correspondance FTS5."""
        if not query or not query.strip():
            return []

        # Nettoyage de la requête pour syntaxe FTS5
        clean_tokens = [re.sub(r"[^\w\s]", "", t) for t in query.split() if t.strip()]
        clean_tokens = [t for t in clean_tokens if t]

        if not clean_tokens:
            return []

        fts_query = " OR ".join([f'"{t}"*' for t in clean_tokens])

        async with aiosqlite.connect(self.db_path) as db:
            # 1. Tentative FTS5 avec BM25 et snippets
            try:
                if tag:
                    sql = """
                        SELECT d.id, d.content, d.metadata, d.tag, snippet(documents_fts, 0, '<b>', '</b>', '...', 12) as snippet, bm25(documents_fts) as rank
                        FROM documents_fts f
                        JOIN documents d ON d.id = f.rowid
                        WHERE documents_fts MATCH ? AND d.tag = ?
                        ORDER BY rank
                        LIMIT ?;
                    """
                    cursor = await db.execute(sql, (fts_query, tag, limit))
                else:
                    sql = """
                        SELECT d.id, d.content, d.metadata, d.tag, snippet(documents_fts, 0, '<b>', '</b>', '...', 12) as snippet, bm25(documents_fts) as rank
                        FROM documents_fts f
                        JOIN documents d ON d.id = f.rowid
                        WHERE documents_fts MATCH ?
                        ORDER BY rank
                        LIMIT ?;
                    """
                    cursor = await db.execute(sql, (fts_query, limit))

                rows = await cursor.fetchall()
                if rows:
                    return [
                        {
                            "id": r[0],
                            "content": r[1],
                            "metadata": json.loads(r[2]) if r[2] else None,
                            "tag": r[3],
                            "snippet": r[4],
                            "score": round(abs(float(r[5])), 4) if r[5] is not None else 0.0,
                        }
                        for r in rows
                    ]
            except Exception as e:
                logger.warning("[RAG] Recherche FTS5 échouée, bascule vers LIKE : %s", e)

            # 2. Fallback SQL LIKE si FTS5 n'a rien renvoyé ou en cas de syntaxe atypique
            like_sql = "SELECT id, content, metadata, tag FROM documents WHERE content LIKE ?"
            params = [f"%{clean_tokens[0]}%"]
            if tag:
                like_sql += " AND tag = ?"
                params.append(tag)
            like_sql += " LIMIT ?"
            params.append(limit)

            cursor = await db.execute(like_sql, tuple(params))
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "content": r[1],
                    "metadata": json.loads(r[2]) if r[2] else None,
                    "tag": r[3],
                    "snippet": r[1][:120] + "..." if len(r[1]) > 120 else r[1],
                    "score": 0.5,
                }
                for r in rows
            ]

    async def delete_document(self, doc_id: int) -> bool:
        """Supprime un document par son identifiant."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM documents WHERE id = ?;", (doc_id,))
            await db.commit()
            return cursor.rowcount > 0
