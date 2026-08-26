from dataclasses import dataclass
from enum import Enum


class ExecutionApproval(str, Enum):
    AUTO_EXECUTE = "AUTO_EXECUTE"
    SUPERVISED_EXECUTE = "SUPERVISED_EXECUTE"
    REQUIRE_HUMAN_APPROVAL = "REQUIRE_HUMAN_APPROVAL"


@dataclass(frozen=True)
class GovernanceDecision:
    approval_status: ExecutionApproval
    action_type: str
    confidence: float
    reason: str


class DecisionGovernor:
    """Filtre les actions préconisées selon les seuils de confiance de l'organisation."""

    def __init__(self, auto_threshold: float = 0.90, supervised_threshold: float = 0.80):
        self.auto_threshold = auto_threshold
        self.supervised_threshold = supervised_threshold

    def govern(self, action_type: str, confidence: float) -> GovernanceDecision:
        if confidence >= self.auto_threshold:
            status = ExecutionApproval.AUTO_EXECUTE
        elif confidence >= self.supervised_threshold:
            status = ExecutionApproval.SUPERVISED_EXECUTE
        else:
            status = ExecutionApproval.REQUIRE_HUMAN_APPROVAL

        return GovernanceDecision(
            approval_status=status,
            action_type=action_type,
            confidence=confidence,
            reason=f"Confidence {confidence} mapped to approval level {status.value}.",
        )
