import json
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any

class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

SEVERITY_SCORES = {
    Severity.INFO: 10,
    Severity.WARNING: 40,
    Severity.HIGH: 70,
    Severity.CRITICAL: 100
}

class IncidentCategory(str, Enum):
    EXTERNAL_TIMEOUT = "EXTERNAL_TIMEOUT"
    SECURITY_CONTEXT_FAILURE = "SECURITY_CONTEXT_FAILURE"
    HANDLER_DEGRADATION = "HANDLER_DEGRADATION"
    RUNTIME_FAILURE = "RUNTIME_FAILURE"
    UNHANDLED_EXCEPTION = "UNHANDLED_EXCEPTION"

@dataclass(frozen=True)
class IncidentBundle:
    """Rapport d'incident forensique immuable avec scellé cryptographique."""
    incident_id: str
    timestamp: str
    severity: str
    severity_score: int
    category: str
    execution_id: str
    action_name: str
    state_trace: List[Dict[str, Any]]
    context_signature_valid: bool
    payload_hash: str
    bundle_hash: str  # Digest SHA-256 scellant l'incident complet
    telemetry_snapshot: Dict[str, Any]
    root_candidates: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def verify_integrity(self) -> bool:
        """Vérifie que le bundle n'a pas été altéré sur disque."""
        canonical = {
            "incident_id": self.incident_id,
            "timestamp": self.timestamp,
            "severity": self.severity,
            "severity_score": self.severity_score,
            "category": self.category,
            "execution_id": self.execution_id,
            "action_name": self.action_name,
            "context_signature_valid": self.context_signature_valid,
            "payload_hash": self.payload_hash
        }
        recalculated = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode('utf-8')).hexdigest()
        return recalculated == self.bundle_hash
