import os
import json
import sqlite3
import hashlib
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

MEMORY_DIR = "runtime/memory"
JSON_CACHE_FILE = os.path.join(MEMORY_DIR, "working_memory.json")
DB_PATH = os.path.join(MEMORY_DIR, "database", "memory.sqlite3")
AUDIT_LOG = os.path.join(MEMORY_DIR, "logs", "memory_audit.log")

class MemoryInteraction(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    user_id: str
    action: str
    details: str
    sentiment: Optional[str] = "neutral"

class WorkingMemorySchema(BaseModel):
    version: str = "4.0-IndustrialCore"
    last_sync: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    interactions: List[MemoryInteraction] = Field(default_factory=list)

class IndustrialMemoryManager:
    """Gestionnaire de mémoire double couche (Fast Cache JSON + SQLite WAL + Ledger Immutable)."""
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(os.path.dirname(AUDIT_LOG), exist_ok=True)
        self._init_db()
        self._ensure_cache()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user_id TEXT,
                action TEXT,
                details TEXT,
                sentiment TEXT
            )""")
            # Ledger immutable avec chaînage de hachage cryptographique
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ledger_audit (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user_id TEXT,
                action TEXT,
                hash TEXT,
                previous_hash TEXT
            )""")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ledger_ts ON ledger_audit(timestamp);")
            conn.commit()

    def _ensure_cache(self):
        if not os.path.exists(JSON_CACHE_FILE):
            self._save_cache(WorkingMemorySchema().model_dump())

    def _save_cache(self, data: dict):
        with open(JSON_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def _get_last_ledger_hash(self, cursor) -> str:
        cursor.execute("SELECT hash FROM ledger_audit ORDER BY event_id DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else "0000000000000000000000000000000000000000000000000000000000000000"

    def record_interaction(self, user_id: str, action: str, details: str, sentiment: str = "neutral") -> bool:
        try:
            interaction = MemoryInteraction(
                user_id=str(user_id), action=action, details=details, sentiment=sentiment
            )
            
            # 1. Écriture permanente SQLite WAL + Ledger
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO interactions (timestamp, user_id, action, details, sentiment)
                VALUES (?, ?, ?, ?, ?)
                """, (interaction.timestamp, interaction.user_id, interaction.action, interaction.details, interaction.sentiment))
                
                # Calcul du hachage pour le Ledger immutable
                prev_hash = self._get_last_ledger_hash(cursor)
                raw_data = f"{prev_hash}|{interaction.timestamp}|{interaction.user_id}|{interaction.action}"
                current_hash = hashlib.sha256(raw_data.encode('utf-8')).hexdigest()
                
                cursor.execute("""
                INSERT INTO ledger_audit (timestamp, user_id, action, hash, previous_hash)
                VALUES (?, ?, ?, ?, ?)
                """, (interaction.timestamp, interaction.user_id, interaction.action, current_hash, prev_hash))
                conn.commit()

            # 2. Mise à jour du Fast Cache JSON (glissant 100 éléments)
            try:
                with open(JSON_CACHE_FILE, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
            except Exception:
                cache_data = WorkingMemorySchema().model_dump()

            cache_data["interactions"].append(interaction.model_dump())
            if len(cache_data["interactions"]) > 100:
                cache_data["interactions"] = cache_data["interactions"][-100:]
            cache_data["last_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_cache(cache_data)

            # 3. Journal audit texte
            log_line = f"[{interaction.timestamp}] [USER:{interaction.user_id}] {interaction.action} -> {interaction.details}\n"
            with open(AUDIT_LOG, "a", encoding="utf-8") as lf:
                lf.write(log_line)

            return True
        except Exception as e:
            print(f"[-] Erreur IndustrialMemoryManager: {e}")
            return False

memory_core = IndustrialMemoryManager()
