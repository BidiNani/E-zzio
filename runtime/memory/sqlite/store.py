import sqlite3
import json
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from runtime.memory.events import RuntimeEvent

class SQLiteEventStore:
    """Stocke les événements bruts en mode append-only avec gestion thread-local des connexions SQLite."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = Path("runtime/memory/sqlite/cognitive_store.db")
        else:
            db_path = Path(db_path) if str(db_path) != ":memory:" else ":memory:"
        
        if str(db_path) != ":memory:":
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
        self.db_path = db_path
        self._local = threading.local()
        self._connections = []
        self._closed = False
        self._lock = threading.RLock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._closed:
            raise RuntimeError("SQLiteEventStore is already closed.")
        
        if not hasattr(self._local, "connection") or self._local.connection is None:
            db_target = ":memory:" if str(self.db_path) == ":memory:" else str(self.db_path)
            conn = sqlite3.connect(
                db_target,
                check_same_thread=False
            )

            conn.row_factory = sqlite3.Row

            with self._lock:
                self._connections.append(conn)

            self._local.connection = conn
            
        return self._local.connection

    def _init_db(self):
        with self._lock:
            conn = self._get_connection()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    retention_score REAL NOT NULL,
                    consolidated INTEGER DEFAULT 0
                )
            """)
            try:
                conn.execute("ALTER TABLE memory_events ADD COLUMN consolidated INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            conn.commit()

    def append_event(self, event: RuntimeEvent, retention_score: float = 1.0):
        with self._lock:
            conn = self._get_connection()
            conn.execute("""
                INSERT OR IGNORE INTO memory_events 
                (event_id, event_type, trace_id, session_id, actor, timestamp, payload, retention_score, consolidated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                event.event_id,
                event.event_type,
                event.trace_id,
                event.session_id,
                event.actor,
                event.timestamp,
                json.dumps(event.payload),
                retention_score
            ))
            conn.commit()

    def get_events_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT * FROM memory_events WHERE session_id = ? ORDER BY timestamp ASC",
                (session_id,)
            )
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_unconsolidated_events(self) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT * FROM memory_events WHERE consolidated = 0 ORDER BY timestamp ASC"
            )
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

    def mark_consolidated(self, event_ids: List[str]):
        if not event_ids or self._closed:
            return
        with self._lock:
            conn = self._get_connection()
            conn.executemany(
                "UPDATE memory_events SET consolidated = 1 WHERE event_id = ?",
                [(eid,) for eid in event_ids]
            )
            conn.commit()

    def close(self):
        """
        Fermeture globale SQLite.
        Ferme toutes les connexions créées par tous les threads.
        """

        with self._lock:

            if self._closed:
                return

            for conn in list(self._connections):
                try:
                    conn.commit()
                except Exception:
                    pass

                try:
                    conn.close()
                except Exception:
                    pass


            self._connections.clear()

            if hasattr(self._local,"connection"):
                self._local.connection = None

            self._closed=True

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "event_id": row["event_id"],
            "event_type": row["event_type"],
            "trace_id": row["trace_id"],
            "session_id": row["session_id"],
            "actor": row["actor"],
            "timestamp": row["timestamp"],
            "payload": json.loads(row["payload"]),
            "retention_score": row["retention_score"],
            "consolidated": bool(row["consolidated"])
        }
