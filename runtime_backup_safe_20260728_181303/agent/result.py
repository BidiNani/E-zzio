from runtime.agent.state_machine import AgentStep

class AgentResult:
    """Encapsule le résultat complet d'une étape d'exécution du pipeline agentique."""
    def __init__(self, step: AgentStep, text: str = "", tool_request=None, tool_result=None):
        self.step = step
        self.text = text
        self.tool_request = tool_request
        self.tool_result = tool_result