import pytest
from runtime.action.state import ExecutionState, validate_transition

def test_valid_state_transitions():
    # Enchaînement nominal valide
    validate_transition(ExecutionState.CREATED, ExecutionState.VALIDATING)
    validate_transition(ExecutionState.VALIDATING, ExecutionState.AUTHORIZED)
    validate_transition(ExecutionState.AUTHORIZED, ExecutionState.RUNNING)
    validate_transition(ExecutionState.RUNNING, ExecutionState.SUCCESS)

def test_invalid_state_transitions():
    # Sauts illicites interdits
    with pytest.raises(RuntimeError, match="Invalid state transition"):
        validate_transition(ExecutionState.CREATED, ExecutionState.SUCCESS)

    with pytest.raises(RuntimeError, match="Invalid state transition"):
        validate_transition(ExecutionState.SUCCESS, ExecutionState.RUNNING)
