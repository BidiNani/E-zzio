from .contracts import AgentStatus


class InvalidTransition(Exception):
    pass


_ALLOWED = {
    AgentStatus.CREATED: [AgentStatus.PLANNING, AgentStatus.HALTED, AgentStatus.FAILED],
    AgentStatus.PLANNING: [AgentStatus.WAITING_APPROVAL, AgentStatus.HALTED],
    AgentStatus.WAITING_APPROVAL: [AgentStatus.EXECUTING, AgentStatus.HALTED],
    AgentStatus.EXECUTING: [AgentStatus.VERIFYING, AgentStatus.FAILED],
    AgentStatus.VERIFYING: [AgentStatus.COMPLETED, AgentStatus.PLANNING, AgentStatus.FAILED],
}


class AgentStateMachine:
    def __init__(self):
        self.state = AgentStatus.CREATED

    def transition(self, target):
        allowed = _ALLOWED.get(self.state, [])
        if target not in allowed:
            raise InvalidTransition(f"{self.state} -> {target} forbidden")
        self.state = target
        return self.state
