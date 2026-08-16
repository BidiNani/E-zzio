from enum import Enum

class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"

class AgentPolicy:
    SAFE_CAPABILITIES = {"sandbox.execute_python"}

    def validate(self, step):
        if step.capability not in self.SAFE_CAPABILITIES:
            return PolicyDecision.DENY
        return PolicyDecision.ALLOW