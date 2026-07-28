import sqlite3
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from runtime.knowledge.models import KnowledgeItem, SourceType

class KnowledgeStore:
    """Long-term operational memory database (ezzio.db) with auto-migration & keyword search."""
    def __init__(self, db_path: str = "data/ezzio.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_items (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    importance REAL DEFAULT 0.5,
                    source_type TEXT DEFAULT 'INTERNAL',
                    source TEXT DEFAULT 'system',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')

            cursor = conn.execute("PRAGMA table_info(knowledge_items)")
            existing_cols = {row[1] for row in cursor.fetchall()}

            migrations = [
                ("importance", "REAL DEFAULT 0.5"),
                ("source_type", "TEXT DEFAULT 'INTERNAL'"),
                ("source", "TEXT DEFAULT 'system'"),
                ("updated_at", "TEXT DEFAULT ''")
            ]
            for col_name, col_def in migrations:
                if col_name not in existing_cols:
                    conn.execute(f"ALTER TABLE knowledge_items ADD COLUMN {col_name} {col_def}")

    def save_item(self, item: KnowledgeItem):
        now = datetime.now(timezone.utc).isoformat()
        updated_at = item.updated_at or now
        source_type_str = str(item.source_type.value if hasattr(item.source_type, 'value') else item.source_type)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                '''INSERT OR REPLACE INTO knowledge_items 
                   (id, category, content, confidence, importance, source_type, source, created_at, updated_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (item.id, item.category, item.content, item.confidence, item.importance, 
                 source_type_str, item.source, item.created_at, updated_at)
            )

    def search_knowledge_by_keywords(self, keywords: List[str], min_importance: float = 0.0) -> List[Dict[str, Any]]:
        """Recherche par extraction de mots-clés intelligents."""
        if not keywords:
            return []
            
        with sqlite3.connect(self.db_path) as conn:
            clauses = ["content LIKE ?"] * len(keywords)
            query_str = f'''
                SELECT id, category, content, confidence, importance, source_type, source, created_at, updated_at 
                FROM knowledge_items 
                WHERE ({' OR '.join(clauses)}) AND importance >= ? 
                ORDER BY importance DESC, confidence DESC
            '''
            params = [f"%{kw}%" for kw in keywords] + [min_importance]
            cursor = conn.execute(query_str, params)
            return [
                {
                    "id": row[0], "category": row[1], "content": row[2],
                    "confidence": row[3], "importance": row[4], "source_type": row[5],
                    "source": row[6], "created_at": row[7], "updated_at": row[8]
                }
                for row in cursor.fetchall()
            ]

    def clear(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM knowledge_items")
