import json
import hashlib
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Any, Optional

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
class Finding:
    """Constat d'analyse structuré produit par la chaîne d'analyseurs."""
    type: str
    confidence: float
    severity: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class IncidentBundle:
    """Rapport d'incident forensique immuable avec scellé cryptographique à 100%."""
    incident_id: str
    timestamp: str
    severity: str
    severity_score: int
    category: str
    execution_id: str
    action_name: str
    trace_id: Optional[str]
    span_id: Optional[str]
    state_trace: List[Dict[str, Any]]
    context_signature_valid: bool
    payload_hash: str
    bundle_hash: str  # SHA-256 scellant 100% du contenu du bundle
    telemetry_snapshot: Dict[str, Any]
    findings: List[Dict[str, Any]]
    root_candidates: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def compute_canonical_hash(self) -> str:
        """Génère l'empreinte SHA-256 canonique sur 100% des données du bundle."""
        canonical = {
            "incident_id": self.incident_id,
            "timestamp": self.timestamp,
            "severity": self.severity,
            "severity_score": self.severity_score,
            "category": self.category,
            "execution_id": self.execution_id,
            "action_name": self.action_name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "state_trace": self.state_trace,
            "context_signature_valid": self.context_signature_valid,
            "payload_hash": self.payload_hash,
            "telemetry_snapshot": self.telemetry_snapshot,
            "findings": self.findings,
            "root_candidates": self.root_candidates,
            "metadata": self.metadata
        }
        raw = json.dumps(canonical, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    def verify_integrity(self) -> bool:
        """Vérifie l'intégrité absolue à 100% du bundle."""
        return self.compute_canonical_hash() == self.bundle_hash
