import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime, timezone

@dataclass(frozen=True)
class RollbackRecord:
    record_id: str
    incident_id: str
    action_type: str
    target_component: str
    previous_state: Dict[str, Any]
    new_state: Dict[str, Any]
    rollback_available: bool

class RollbackManager:
    """Consigne et restaure l'état antérieur des composants du runtime."""

    def __init__(self, db_path: str = "data/incidents.db"):
        self.db_path = db_path
        self._db_lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        with self._db_lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
            try:
                with conn:
                    conn.execute("PRAGMA journal_mode=WAL;")
                    conn.execute('''
                        CREATE TABLE IF NOT EXISTS rollback_history (
                            record_id TEXT PRIMARY KEY,
                            incident_id TEXT NOT NULL,
                            action_type TEXT NOT NULL,
                            target_component TEXT NOT NULL,
                            previous_state TEXT NOT NULL,
                            new_state TEXT NOT NULL,
                            rollback_available INTEGER NOT NULL,
                            timestamp TEXT NOT NULL,
                            restored_at TEXT
                        )
                    ''')
            finally:
                conn.close()

    def record_change(self, incident_id: str, action_type: str, target: str, prev_state: Dict[str, Any], new_state: Dict[str, Any]) -> RollbackRecord:
        record_id = f"rb_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        rec = RollbackRecord(
            record_id=record_id,
            incident_id=incident_id,
            action_type=action_type,
            target_component=target,
            previous_state=prev_state,
            new_state=new_state,
            rollback_available=True
        )
        with self._db_lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
            try:
                with conn:
                    conn.execute('''
                        INSERT INTO rollback_history (record_id, incident_id, action_type, target_component, previous_state, new_state, rollback_available, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        rec.record_id, rec.incident_id, rec.action_type, rec.target_component,
                        json.dumps(rec.previous_state, default=str),
                        json.dumps(rec.new_state, default=str),
                        1, now
                    ))
            finally:
                conn.close()
        return rec

    def restore(self, record_id: str, executors: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Exécute l'action inverse et invalide la réutilisation du rollback."""
        with self._db_lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
            try:
                cursor = conn.execute("SELECT record_id, action_type, previous_state, rollback_available FROM rollback_history WHERE record_id = ?", (record_id,))
                row = cursor.fetchone()
                if not row:
                    return {"status": "FAILED", "reason": f"Rollback record '{record_id}' not found."}
                
                _, action_type, prev_state_json, available = row
                if not available:
                    return {"status": "FAILED", "reason": f"Rollback '{record_id}' has already been executed or invalidated."}

                previous_state = json.loads(prev_state_json)
                executor = executors.get(action_type)
                if not executor or not hasattr(executor, "restore"):
                    return {"status": "FAILED", "reason": f"No restore capability for action '{action_type}'."}

                # Appliquer la restauration d'état
                restore_res = executor.restore(previous_state, context or {})
                now = datetime.now(timezone.utc).isoformat()

                with conn:
                    conn.execute("UPDATE rollback_history SET rollback_available = 0, restored_at = ? WHERE record_id = ?", (now, record_id))

                return {
                    "status": "SUCCESS",
                    "record_id": record_id,
                    "restored_state": previous_state,
                    "execution_details": restore_res
                }
            finally:
                conn.close()
