import aiosqlite
from typing import Any, Dict, List, Optional
import os

class SimpleRAG:
    """RAG minimal pour stockage et retrieval de documents."""
    
    def __init__(self, db_path: str = "runtime/rag/documents.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_content ON documents(content)
            """)
            await db.commit()
    
    async def add_document(self, content: str, metadata: Dict[str, Any] = None) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO documents (content, metadata) VALUES (?, ?)",
                (content, str(metadata) if metadata else None)
            )
            await db.commit()
            return cursor.lastrowid
    
    async def search_documents(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, content, metadata FROM documents WHERE content LIKE ? LIMIT ?",
                (f"%{query}%", limit)
            )
            rows = await cursor.fetchall()
            return [
                {"id": row[0], "content": row[1], "metadata": row[2]}
                for row in rows
            ]
