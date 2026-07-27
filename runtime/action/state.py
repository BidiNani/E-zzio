from enum import Enum

class ExecutionState(Enum):
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    AUTHORIZED = "AUTHORIZED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    QUARANTINED = "QUARANTINED"
    SIMULATED = "SIMULATED"

# Matrice stricte des transitions autorisées (Empêche les sauts illicites type CREATED -> SUCCESS)
VALID_TRANSITIONS = {
    ExecutionState.CREATED: [ExecutionState.VALIDATING, ExecutionState.QUARANTINED],
    ExecutionState.VALIDATING: [ExecutionState.AUTHORIZED, ExecutionState.FAILED, ExecutionState.QUARANTINED],
    ExecutionState.AUTHORIZED: [ExecutionState.RUNNING, ExecutionState.SIMULATED, ExecutionState.FAILED],
    ExecutionState.RUNNING: [ExecutionState.SUCCESS, ExecutionState.FAILED, ExecutionState.TIMEOUT, ExecutionState.CANCELLED],
    ExecutionState.SUCCESS: [],
    ExecutionState.FAILED: [],
    ExecutionState.TIMEOUT: [],
    ExecutionState.CANCELLED: [],
    ExecutionState.QUARANTINED: [],
    ExecutionState.SIMULATED: []
}

def validate_transition(current: ExecutionState, target: ExecutionState):
    """Valide qu'une transition d'état respecte la machine à états du kernel."""
    allowed = VALID_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise RuntimeError(f"Invalid state transition: {current.value} -> {target.value}")
