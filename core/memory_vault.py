import re
from pathlib import Path
from typing import Optional
from core.storage import storage

DB_PATH = Path(r"G:\\AI\\E-zzio\\runtime\\state\\deterministic_memory.db")


def _init_db():
    with storage.get_connection(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_kv (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


_init_db()


def check_memory_intent(user_prompt: str) -> Optional[str]:
    p = str(user_prompt).strip()
    if not p:
        return None

    m_set = re.search(r"(?:retiens|m[ée]morise|enregistre)\s+(?:que\s+)?(?:le\s+|la\s+)?(.+?)\s+(?:est|=|:)\s+(.+)", p, re.IGNORECASE)
    if not m_set:
        m_set = re.search(
            r"(?:retiens|m[ée]morise|enregistre)\s+(?:le\s+code\s+secret|la\s+valeur|le\s+code)\s+([a-zA-Z0-9_-]+)", p, re.IGNORECASE
        )
        if m_set:
            k, v = "code secret", m_set.group(1).strip()
        else:
            k, v = None, None
    else:
        k, v = m_set.group(1).strip().lower(), m_set.group(2).strip()

    if k and v:
        with storage.get_connection(DB_PATH) as conn:
            conn.execute("INSERT OR REPLACE INTO session_kv (key, value) VALUES (?, ?)", (k, v))
        return f"C'est noté. J'ai mémorisé que {k} est : {v}."

    m_get = re.search(r"(?:quel|quelle)\s+est\s+(?:le\s+|la\s+)?(.+?)(?:\s*\?|\s+dont|\Z)", p, re.IGNORECASE)
    if not m_get:
        m_get = re.search(r"c['’]est\s+quoi\s+(?:le\s+|la\s+)?(.+?)(?:\s*\?|\Z)", p, re.IGNORECASE)

    if m_get:
        k_search = m_get.group(1).strip().lower()
        with storage.get_connection(DB_PATH) as conn:
            row = conn.execute("SELECT value FROM session_kv WHERE key = ? OR key LIKE ?", (k_search, f"%{k_search}%")).fetchone()
            if row:
                return f"Le {k_search} enregistré est : {row[0]}."

    return None
