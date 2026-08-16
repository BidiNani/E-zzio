from __future__ import annotations
from enum import Enum
import json
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional

from .model import IncidentRecord
from .classifier import IncidentClassification, IncidentAction

@dataclass
class DecisionRecord:
    decision_id: str
    incident_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    action_taken: IncidentAction = IncidentAction.LOG_ONLY
    operator: str = "auto_governance_controller"
    justification: str = ""
    evidence_payload_hash: str = ""
    decision_hash: Optional[str] = None

    def compute_decision_hash(self) -> str:
        """Calcule un hachage cryptographique déterministe de la décision de gouvernance."""
        data = {
            "decision_id": self.decision_id,
            "incident_id": self.incident_id,
            "timestamp": self.timestamp,
            "action_taken": self.action_taken.value if isinstance(self.action_taken, Enum) else self.action_taken,
            "operator": self.operator,
            "justification": self.justification,
            "evidence_payload_hash": self.evidence_payload_hash
        }
        serialized = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["action_taken"] = self.action_taken.value if isinstance(self.action_taken, Enum) else self.action_taken
        return d

class DecisionGovernanceLayer:
    """
    Couche de décision de gouvernance pour V4.4.
    Transforme la classification d'un incident en une décision formelle et traçable,
    sans interférer avec les mécanismes du noyau V4.2.
    """
    def evaluate_and_decide(
        self,
        record: IncidentRecord,
        classification: IncidentClassification,
        operator: str = "auto_governance_controller"
    ) -> DecisionRecord:
        import uuid
        decision_id = str(uuid.uuid4())
        
        # La décision adopte l'action recommandée par le classificateur de manière déterministe
        action = classification.recommended_action
        justification = f"Automated decision based on classification rationale: {classification.rationale}"
        
        record_hash = record.payload_hash or record.compute_payload_hash()

        decision = DecisionRecord(
            decision_id=decision_id,
            incident_id=record.incident_id,
            action_taken=action,
            operator=operator,
            justification=justification,
            evidence_payload_hash=record_hash
        )
        decision.decision_hash = decision.compute_decision_hash()
        return decision