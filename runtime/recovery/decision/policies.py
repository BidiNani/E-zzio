import json
import os
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass(frozen=True)
class RemediationAction:
    action_type: str
    parameters: Dict[str, Any]
    reason: str
    confidence: float


class RecoveryPolicyEngine:
    """Charge les règles depuis config/recovery_policy.json et évalue l'action corrective."""

    def __init__(self, config_path: str = "config/recovery_policy.json"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "security": {"quarantine_threshold": 100},
            "queue": {"congestion_threshold": 5000, "scale_batch_size": 200},
            "timeout": {"max_retries": 3, "backoff_factor": 2.0},
        }

    def evaluate(
        self, incident_category: str, severity_score: int, telemetry_snapshot: Dict[str, Any], root_candidates: List[str]
    ) -> RemediationAction:
        sec_cfg = self.config.get("security", {})
        queue_cfg = self.config.get("queue", {})
        time_cfg = self.config.get("timeout", {})

        if incident_category == "SECURITY_CONTEXT_FAILURE" or severity_score >= sec_cfg.get("quarantine_threshold", 100):
            return RemediationAction(
                action_type="QUARANTINE_HANDLER",
                parameters={"scope": "immediate_isolation"},
                reason="Critical security violation or HMAC tampering detected.",
                confidence=1.0,
            )

        queue_size = telemetry_snapshot.get("queue_current_size", 0)
        threshold = queue_cfg.get("congestion_threshold", 5000)
        if queue_size > threshold or any("CONGESTION" in str(c) for c in root_candidates):
            return RemediationAction(
                action_type="SCALE_BATCH_SIZE",
                parameters={"new_batch_size": queue_cfg.get("scale_batch_size", 200)},
                reason="High queue congestion detected; expanding ingestion batch size.",
                confidence=0.92,
            )

        if incident_category == "EXTERNAL_TIMEOUT":
            return RemediationAction(
                action_type="RETRY_BACKOFF",
                parameters={"max_retries": time_cfg.get("max_retries", 3), "backoff_factor": time_cfg.get("backoff_factor", 2.0)},
                reason="External dependency timeout; scheduling exponential backoff retry.",
                confidence=0.85,
            )

        return RemediationAction(
            action_type="NO_ACTION",
            parameters={},
            reason="Incident recorded; severity does not mandate automated remediation.",
            confidence=1.0,
        )
