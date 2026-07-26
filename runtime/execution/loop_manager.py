from runtime.execution.context import ExecutionContext
from runtime.execution.state import ExecutionState


class ExecutionLoopManager:

    """
    Secure lifecycle controller.

    No execution without capability.
    """

    def __init__(self):
        self.active = {}


    def register(self, context: ExecutionContext):

        if not context.has_capability():
            context.state = ExecutionState.BLOCKED
            return False

        context.state = ExecutionState.AUTHORIZED

        self.active[context.execution_id]=context

        return True


    def get(self, execution_id):

        return self.active.get(execution_id)
