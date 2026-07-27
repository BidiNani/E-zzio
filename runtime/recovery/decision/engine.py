import json
import sqlite3
import threading
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from runtime.recovery.contracts import IncidentBundle
from runtime.recovery.decision.policies import RecoveryPolicyEngine, RemediationAction
from runtime.recovery.decision.governor import DecisionGovernor, ExecutionApproval
from runtime.recovery.rollback.manager import RollbackManager
from runtime.recovery.executor.quarantine import QuarantineExecutor
from runtime.recovery.executor.scaling import ScalingExecutor
from runtime.recovery.executor.retry import RetryExecutor
from runtime.telemetry.collector import TelemetryCollector
from runtime.telemetry.events import TelemetryEvent, EventType

class AutonomousRecoveryEngine:
    """Orchestre la boucle complète : Incident -> Policy -> Governor -> Executor -> Rollback -> Audit."""

    def __init__(
        self,
        policy_engine: Optional[RecoveryPolicyEngine] = None,
        governor: Optional[DecisionGovernor] = None,
        rollback_manager: Optional[RollbackManager] = None,
        collector: Optional[TelemetryCollector] = None,
        db_path: str = "data/incidents.db"
    ):
        self.policy_engine = policy_engine or RecoveryPolicyEngine()
        self.governor = governor or DecisionGovernor()
        self.rollback_manager = rollback_manager or RollbackManager(db_path=db_path)
        self.collector = collector or TelemetryCollector()
        self.db_path = db_path
        self._db_lock = threading.RLock()
        
        # Table d'exécuteurs d'actions
        self.executors = {
            "QUARANTINE_HANDLER": QuarantineExecutor(),
            "SCALE_BATCH_SIZE": ScalingExecutor(target_collector=self.collector),
            "RETRY_BACKOFF": RetryExecutor()
        }
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
                            decision_trace_id TEXT NOT NULL,
                            incident_id TEXT NOT NULL,
                            action_type TEXT NOT NULL,
                            parameters TEXT NOT NULL,
                            approval_status TEXT NOT NULL,
                            execution_status TEXT NOT NULL,
                            reason TEXT NOT NULL,
                            confidence REAL NOT NULL,
                            executed_at TEXT NOT NULL
                        )
                    ''')
            finally:
                conn.close()

    def process_incident(self, bundle: IncidentBundle) -> Dict[str, Any]:
        decision_trace_id = f"dt_{uuid.uuid4().hex[:8]}"
        
        # 1. Évaluation Politique
        action = self.policy_engine.evaluate(
            incident_category=bundle.category,
            severity_score=bundle.severity_score,
            telemetry_snapshot=bundle.telemetry_snapshot,
            root_candidates=bundle.root_candidates
        )

        # 2. Arbitrage du Gouverneur
        gov_decision = self.governor.govern(
            action_type=action.action_type,
            confidence=action.confidence
        )

        execution_result = {"status": "SKIPPED", "reason": "Requires human approval"}
        rollback_record_id = None

        # 3. Exécution si approuvé
        if gov_decision.approval_status in [ExecutionApproval.AUTO_EXECUTE, ExecutionApproval.SUPERVISED_EXECUTE]:
            executor = self.executors.get(action.action_type)
            if executor:
                ctx = {"action_name": bundle.action_name, "execution_id": bundle.execution_id}
                execution_result = executor.execute(action.parameters, context=ctx)
                
                # 4. Consignation Rollback
                prev_state = execution_result.get("previous_state", {})
                new_state = execution_result.get("new_state", {})
                target_comp = execution_result.get("target", bundle.action_name)
                
                rb_rec = self.rollback_manager.record_change(
                    incident_id=bundle.incident_id,
                    action_type=action.action_type,
                    target=target_comp,
                    prev_state=prev_state,
                    new_state=new_state
                )
                rollback_record_id = rb_rec.record_id

        # 5. Persistance de la Decision Trace
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._db_lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
            try:
                with conn:
                    conn.execute('''
                        INSERT INTO remediation_actions 
                        (decision_trace_id, incident_id, action_type, parameters, approval_status, execution_status, reason, confidence, executed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        decision_trace_id,
                        bundle.incident_id,
                        action.action_type,
                        json.dumps(action.parameters, default=str),
                        gov_decision.approval_status.value,
                        execution_result.get("status", "UNKNOWN"),
                        action.reason,
                        action.confidence,
                        timestamp
                    ))
            finally:
                conn.close()

        # 6. Émission vers Evidence Ledger
        self.collector.record_event(TelemetryEvent(
            event_type=EventType.SYSTEM_HEALTH_CHECK,
            payload={
                "event": "REMEDIATION_EXECUTED",
                "decision_trace_id": decision_trace_id,
                "incident_id": bundle.incident_id,
                "action_type": action.action_type,
                "approval_status": gov_decision.approval_status.value,
                "execution_status": execution_result.get("status", "UNKNOWN"),
                "rollback_record_id": rollback_record_id
            }
        ))

        return {
            "decision_trace_id": decision_trace_id,
            "incident_id": bundle.incident_id,
            "action_type": action.action_type,
            "approval_status": gov_decision.approval_status.value,
            "execution_result": execution_result,
            "rollback_record_id": rollback_record_id,
            "confidence": action.confidence
        }
