from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass(frozen=True)
class RemediationAction:
    action_type: str  # ex: "SCALE_BATCH_SIZE", "QUARANTINE_HANDLER", "RETRY_BACKOFF", "NO_ACTION"
    parameters: Dict[str, Any]
    reason: str
    confidence: float

class RecoveryPolicyEngine:
    """Moteur de décision politique : évalue un incident et prescrit une action contrôlée."""

    def evaluate(self, incident_category: str, severity_score: int, telemetry_snapshot: Dict[str, Any], root_candidates: list) -> RemediationAction:
        
        # Règle 1 : Sûreté critique (Attaque HMAC / Security Violation) -> Quarantaine absolue
        if incident_category == "SECURITY_CONTEXT_FAILURE" or severity_score >= 100:
            return RemediationAction(
                action_type="QUARANTINE_HANDLER",
                parameters={"scope": "immediate_isolation"},
                reason="Critical security violation or HMAC tampering detected.",
                confidence=1.0
            )

        # Règle 2 : Saturation de file / Pression I/O -> Ajustement dynamique du batch_size
        queue_size = telemetry_snapshot.get("queue_current_size", 0)
        if queue_size > 5000 or any("CONGESTION" in str(c) for c in root_candidates):
            return RemediationAction(
                action_type="SCALE_BATCH_SIZE",
                parameters={"new_batch_size": 200},
                reason="High queue congestion detected; expanding ingestion batch size.",
                confidence=0.92
            )

        # Règle 3 : Timeout externe persistant -> Stratégie de Retry avec Backoff
        if incident_category == "EXTERNAL_TIMEOUT":
            return RemediationAction(
                action_type="RETRY_BACKOFF",
                parameters={"max_retries": 3, "backoff_factor": 2.0},
                reason="External dependency timeout; scheduling exponential backoff retry.",
                confidence=0.85
            )

        # Défaut : Aucune action automatisée risquée sans validation humaine
        return RemediationAction(
            action_type="NO_ACTION",
            parameters={},
            reason="Incident recorded; severity does not mandate automated remediation.",
            confidence=1.0
        )
