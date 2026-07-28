from enum import Enum

class AgentStep(Enum):
    RESPONSE = "response"
    TOOL_REQUEST = "tool_request"
    SECURITY_BLOCK = "security_block"
    ERROR = "error"