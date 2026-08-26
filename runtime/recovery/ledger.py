import sqlite3
import os
import json
import hashlib
import threading
from typing import Dict, Any
from datetime import datetime, timezone


class RecoveryLedger:
    """Registre cryptographique immuable retraçant l'ensemble du cycle de vie des remédiations."""

    def __init__(self, db_path: str = "data/incidents.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._db_lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        with self._db_lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
            try:
                with conn:
                    conn.execute("PRAGMA journal_mode=WAL;")
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS recovery_ledger (
                            entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            incident_id TEXT NOT NULL,
                            decision_trace_id TEXT NOT NULL,
                            action_type TEXT NOT NULL,
                            before_state_hash TEXT NOT NULL,
                            after_state_hash TEXT NOT NULL,
                            decision_signature TEXT NOT NULL,
                            ledger_hash TEXT NOT NULL,
                            timestamp TEXT NOT NULL
                        )
                    """)
            finally:
                conn.close()

    def record_recovery_event(
        self,
        incident_id: str,
        decision_trace_id: str,
        action_type: str,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        decision_signature: str,
    ) -> str:
        before_hash = hashlib.sha256(json.dumps(before_state, sort_keys=True, default=str).encode()).hexdigest()
        after_hash = hashlib.sha256(json.dumps(after_state, sort_keys=True, default=str).encode()).hexdigest()
        timestamp = datetime.now(timezone.utc).isoformat()

        raw_canonical = f"{incident_id}|{decision_trace_id}|{action_type}|{before_hash}|{after_hash}|{decision_signature}|{timestamp}"
        ledger_hash = hashlib.sha256(raw_canonical.encode("utf-8")).hexdigest()

        with self._db_lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO recovery_ledger
                        (incident_id, decision_trace_id, action_type, before_state_hash, after_state_hash, decision_signature, ledger_hash, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (incident_id, decision_trace_id, action_type, before_hash, after_hash, decision_signature, ledger_hash, timestamp),
                    )
            finally:
                conn.close()

        return ledger_hash
