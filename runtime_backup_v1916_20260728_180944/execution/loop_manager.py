from runtime.execution.context import ExecutionContext
from runtime.execution.state import ExecutionState


class ExecutionLoopManager:
    """
    Secure execution lifecycle controller.

    Rule:
    No capability => No execution.
    """

    def __init__(self):
        self.active = {}

    def register(
        self,
        context: ExecutionContext,
        capability_verifier
    ):
        """
        Registers execution only after capability validation.
        """
        if not context.has_capability():
            context.state = ExecutionState.BLOCKED
            return False

        if not capability_verifier(context.capability_id):
            context.state = ExecutionState.EXPIRED
            return False

        context.state = ExecutionState.AUTHORIZED
        self.active[
            context.execution_id
        ] = context

        return True

    def get(self, execution_id):
        return self.active.get(execution_id)

    def remove(self, execution_id):
        return self.active.pop(
            execution_id,
            None
        )
