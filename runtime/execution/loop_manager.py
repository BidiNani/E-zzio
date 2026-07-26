from runtime.execution.context import ExecutionContext
from runtime.execution.state import ExecutionState


class ExecutionLoopManager:
    """
    Secure lifecycle controller with capability validation.
    """

    def __init__(self):
        self.active = {}

    def register(self, context: ExecutionContext, capability_verifier=None):
        """
        Registers an execution context, enforcing capability checks.
        """
        if not context.has_capability():
            context.state = ExecutionState.BLOCKED
            return False

        # Hook de vérification réelle du jeton si fourni
        if capability_verifier and not capability_verifier(context.capability_id):
            context.state = ExecutionState.EXPIRED
            return False

        context.state = ExecutionState.AUTHORIZED
        self.active[context.execution_id] = context
        return True

    def get(self, execution_id):
        return self.active.get(execution_id)
