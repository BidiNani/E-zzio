"""
Gestionnaire de fenêtrage glissant de contexte et de persistance mémorielle pour E-ZzIO.
"""

import json
import sqlite3
import logging
from pathlib import Path
from typing import Any

from ezzio.config import settings
from ezzio.memory.token_compressor import get_token_compressor

logger = logging.getLogger("EzzioContextWindow")


class ContextWindowManager:
    def __init__(
        self,
        db_path: Path | str = settings.state_db_path,
        max_context_tokens: int = 4000,
        keep_last_turns: int = 5,
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_tokens = max_context_tokens
        self.keep_turns = keep_last_turns
        self.compressor = get_token_compressor()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_thread_id ON conversation_history(thread_id);
            """)
            conn.commit()

    def add_message(self, thread_id: str, role: str, content: str) -> None:
        """Ajoute un message à l'historique d'un thread."""
        compressed_content = self.compressor.compress_text(content)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO conversation_history (thread_id, role, content) VALUES (?, ?, ?)",
                (thread_id, role, compressed_content)
            )
            conn.commit()

    def get_pruned_context(self, thread_id: str) -> list[dict[str, str]]:
        """Récupère l'historique élagué et compressé pour le thread spécifié."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content FROM conversation_history WHERE thread_id = ? ORDER BY rowid ASC",
                (thread_id,)
            )
            rows = cursor.fetchall()

        raw_messages = [{"role": r[0], "content": r[1]} for r in rows]
        pruned, _ = self.compressor.prune_messages(
            raw_messages,
            max_tokens=self.max_tokens,
            keep_last_turns=self.keep_turns
        )
        return pruned

    def clear_thread(self, thread_id: str) -> int:
        """Supprime l'historique d'un thread."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM conversation_history WHERE thread_id = ?", (thread_id,))
            deleted = cursor.rowcount
            conn.commit()
            return deleted


_GLOBAL_CONTEXT_MANAGER: ContextWindowManager | None = None


def get_context_manager() -> ContextWindowManager:
    global _GLOBAL_CONTEXT_MANAGER
    if _GLOBAL_CONTEXT_MANAGER is None:
        _GLOBAL_CONTEXT_MANAGER = ContextWindowManager()
    return _GLOBAL_CONTEXT_MANAGER
