from runtime.execution.state import ExecutionState


class ExecutionLifecycle:


    @staticmethod
    def transition(context, new_state):

        context.state = new_state

        return context
