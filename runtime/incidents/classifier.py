from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List

from .model import IncidentRecord, IncidentSeverity, IncidentCategory


class IncidentAction(str, Enum):
    LOG_ONLY = "LOG_ONLY"
    ALERT = "ALERT"
    RECOVER = "RECOVER"
    FORCE_HALT = "FORCE_HALT"


@dataclass
class IncidentClassification:
    incident_id: str
    recommended_action: IncidentAction
    priority_score: int
    tags: List[str] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "recommended_action": self.recommended_action.value if isinstance(self.recommended_action, Enum) else self.recommended_action,
            "priority_score": self.priority_score,
            "tags": self.tags,
            "rationale": self.rationale,
        }


class IncidentClassifier:
    """
    Classificateur déterministe d'incidents pour la couche V4.4 Incident Governance.
    Analyse les enregistrements d'incidents et recommande une action de gouvernance
    de manière purement analytique, sans droit de mutation sur le noyau V4.2.
    """

    def classify(self, record: IncidentRecord) -> IncidentClassification:
        error_type = record.error_type.upper()
        message = record.message.lower()

        action = IncidentAction.LOG_ONLY
        score = 10
        tags = ["v4.4", "governance"]
        rationale = "Standard execution log."

        if record.severity == IncidentSeverity.PANIC or "panic" in message or "halt" in record.runtime_state.lower():
            action = IncidentAction.FORCE_HALT
            score = 100
            tags.append("critical-failure")
            rationale = "Runtime reached PANIC/HALTED or panic signal detected."
        elif record.category == IncidentCategory.TRUST_VIOLATION or "signature" in error_type or "signature" in message:
            action = IncidentAction.FORCE_HALT
            score = 90
            tags.append("trust-compromise")
            rationale = "Trust registry or signature verification failure."
        elif record.category == IncidentCategory.CAPABILITY_BREACH:
            action = IncidentAction.ALERT
            score = 70
            tags.append("capability-breach")
            rationale = "Unauthorized capability access or invalid manifest."
        elif record.category == IncidentCategory.RESOURCE_EXHAUSTION or "timeout" in error_type.lower():
            action = IncidentAction.RECOVER
            score = 60
            tags.append("resource-exhaustion")
            rationale = "Resource governor limit or execution timeout exceeded; eligible for recovery evaluation."
        elif record.severity == IncidentSeverity.CRITICAL:
            action = IncidentAction.ALERT
            score = 80
            tags.append("high-severity")
            rationale = "Critical severity incident requiring attention."

        return IncidentClassification(
            incident_id=record.incident_id, recommended_action=action, priority_score=score, tags=tags, rationale=rationale
        )
