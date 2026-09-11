"""
E-ZZIO Sovereign Governance — Human-in-the-Loop (HITL) Approval Package.
Fournit la gestion d'approbation humaine déterministe hors Frozen Core.
"""
from core.governance.approval.models import (
    ApprovalStatus,
    DecisionChoice,
    ApprovalRequest,
    ApprovalDecision,
    ExecutionState,
)
from core.governance.approval.manager import (
    ApprovalManager,
    approval_manager,
    PayloadIntegrityViolation,
    ApprovalExpiredError,
    StateTransitionError,
    DoubleExecutionError,
    ContextMismatchError,
)

__all__ = [
    "ApprovalStatus",
    "DecisionChoice",
    "ApprovalRequest",
    "ApprovalDecision",
    "ExecutionState",
    "ApprovalManager",
    "approval_manager",
    "PayloadIntegrityViolation",
    "ApprovalExpiredError",
    "StateTransitionError",
    "DoubleExecutionError",
    "ContextMismatchError",
]
