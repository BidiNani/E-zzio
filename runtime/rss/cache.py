import sqlite3
import os
from typing import List, Dict, Any


class RSSCacheStore:
    """Manages the real-world perception cache database (rss_cache.db)."""

    def __init__(self, db_path: str = "data/rss_cache.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    guid TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    link TEXT NOT NULL,
                    summary TEXT,
                    published_at TEXT,
                    ingested_at TEXT NOT NULL
                )
            """)

    def save_article(self, guid: str, title: str, link: str, summary: str, published_at: str):
        import datetime

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO articles (guid, title, link, summary, published_at, ingested_at) VALUES (?, ?, ?, ?, ?, ?)",
                (guid, title, link, summary, published_at, now),
            )

    def get_recent_articles(self, limit: int = 10) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT guid, title, link, summary, published_at FROM articles ORDER BY ingested_at DESC LIMIT ?", (limit,)
            )
            return [
                {"guid": row[0], "title": row[1], "link": row[2], "summary": row[3], "published_at": row[4]} for row in cursor.fetchall()
            ]

    def clear(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM articles")
