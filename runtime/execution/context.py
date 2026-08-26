from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class ExecutionContext:
    """
    Secure execution envelope.

    Every execution must carry:
    - identity
    - session
    - authorized capability
    - audit correlation
    """

    @property
    def state(self):
        if not hasattr(self, "_state"):
            object.__setattr__(self, "_state", {})
        return self._state

    @state.setter
    def state(self, value):
        object.__setattr__(self, "_state", value)

    execution_id: str
    session_id: str

    capability_id: Optional[str]

    tool_request: Dict[str, Any]

    created_at: datetime = field(default_factory=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc))

    timeout: float = 30.0

    budget: float = 100.0

    audit_id: Optional[str] = None

    state: str = "REQUESTED"

    def has_capability(self) -> bool:
        return self.capability_id is not None
