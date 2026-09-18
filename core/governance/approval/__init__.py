"""
E-ZZIO Sovereign Governance — Human-in-the-Loop (HITL) Approval Package.
Fournit la gestion d'approbation humaine déterministe hors Frozen Core.
"""
from core.governance.approval.manager import (
    ApprovalExpiredError,
    ApprovalManager,
    ContextMismatchError,
    DoubleExecutionError,
    PayloadIntegrityViolation,
    StateTransitionError,
    approval_manager,
)
from core.governance.approval.models import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStatus,
    DecisionChoice,
    ExecutionState,
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
