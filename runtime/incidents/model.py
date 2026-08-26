from __future__ import annotations
import json
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class IncidentSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    PANIC = "PANIC"


class IncidentCategory(str, Enum):
    BOOT_FAILURE = "BOOT_FAILURE"
    TRUST_VIOLATION = "TRUST_VIOLATION"
    CAPABILITY_BREACH = "CAPABILITY_BREACH"
    RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"
    FSM_TRANSITION = "FSM_TRANSITION"
    EXECUTION_ERROR = "EXECUTION_ERROR"


@dataclass
class IncidentRecord:
    incident_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    severity: IncidentSeverity = IncidentSeverity.INFO
    category: IncidentCategory = IncidentCategory.EXECUTION_ERROR
    source: str = "kernel.unknown"
    phase: str = "PRE_BOOT"
    error_type: str = "GENERIC_ERROR"
    message: str = ""
    context_hash: str = ""
    runtime_state: str = "PRE_BOOT"
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    resolved: bool = False
    previous_hash: Optional[str] = None
    payload_hash: Optional[str] = None

    def compute_payload_hash(self) -> str:
        """Calcule le hash cryptographique déterministe du payload de l'incident (sans le previous_hash)."""
        payload_data = {
            "incident_id": self.incident_id,
            "timestamp": self.timestamp,
            "severity": self.severity.value if isinstance(self.severity, Enum) else self.severity,
            "category": self.category.value if isinstance(self.category, Enum) else self.category,
            "source": self.source,
            "phase": self.phase,
            "error_type": self.error_type,
            "message": self.message,
            "context_hash": self.context_hash,
            "runtime_state": self.runtime_state,
            "evidence": self.evidence,
            "resolved": self.resolved,
        }
        serialized = json.dumps(payload_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value if isinstance(self.severity, Enum) else self.severity
        d["category"] = self.category.value if isinstance(self.category, Enum) else self.category
        return d
