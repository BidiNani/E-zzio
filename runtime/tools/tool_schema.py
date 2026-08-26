import uuid
from typing import Optional


class ToolResult:
    def __init__(self, success: bool, output: str, error: Optional[str] = None):
        self.success = success
        self.output = output
        self.error = error or ""

    def to_dict(self) -> dict:
        return {"success": self.success, "output": self.output, "error": self.error}

    def __repr__(self):
        status = "SUCCESS" if self.success else "FAILED"
        return f"<ToolResult [{status}]: {self.output[:60]}...>"


class ToolRequest:
    def __init__(self, name: str, arguments: dict, requester: str = "llm"):
        self.request_id = uuid.uuid4().hex[:12]
        self.name = name
        self.arguments = arguments
        self.requester = requester

    def to_dict(self) -> dict:
        return {"request_id": self.request_id, "name": self.name, "arguments": self.arguments, "requester": self.requester}

    def __repr__(self):
        return f"<ToolRequest [{self.request_id}] {self.name}({self.arguments})>"
