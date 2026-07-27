import json
import sqlite3
import threading
from typing import Dict, Any, Optional
from runtime.recovery.contracts import IncidentBundle
from runtime.recovery.decision.policies import RecoveryPolicyEngine, RemediationAction

class AutonomousRecoveryEngine:
    """Orchestre la boucle de décision autonome et consigne les actions correctives."""

    def __init__(self, policy_engine: Optional[RecoveryPolicyEngine] = None, db_path: str = "data/incidents.db"):
        self.policy_engine = policy_engine or RecoveryPolicyEngine()
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
                        CREATE TABLE IF NOT EXISTS remediation_actions (
                            action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            incident_id TEXT NOT NULL,
                            action_type TEXT NOT NULL,
                            parameters TEXT NOT NULL,
                            reason TEXT NOT NULL,
                            confidence REAL NOT NULL,
                            executed_at TEXT NOT NULL
                        )
                    ''')
            finally:
                conn.close()  # Fermeture obligatoire pour libérer le lock Windows

    def process_incident(self, bundle: IncidentBundle) -> RemediationAction:
        """Évalue l'incident et applique la politique de remédiation contrôlée."""
        action = self.policy_engine.evaluate(
            incident_category=bundle.category,
            severity_score=bundle.severity_score,
            telemetry_snapshot=bundle.telemetry_snapshot,
            root_candidates=bundle.root_candidates
        )

        # Journalisation de l'action corrective dans SQLite
        timestamp = bundle.timestamp
        with self._db_lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
            try:
                with conn:
                    conn.execute('''
                        INSERT INTO remediation_actions (incident_id, action_type, parameters, reason, confidence, executed_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        bundle.incident_id,
                        action.action_type,
                        json.dumps(action.parameters, default=str),
                        action.reason,
                        action.confidence,
                        timestamp
                    ))
            finally:
                conn.close()

        return action
