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

    execution_id: str
    session_id: str

    capability_id: Optional[str]

    tool_request: Dict[str, Any]

    created_at: datetime = field(
        default_factory=datetime.utcnow
    )

    timeout: float = 30.0

    budget: float = 100.0

    audit_id: Optional[str] = None

    state: str = "REQUESTED"


    def has_capability(self) -> bool:
        return self.capability_id is not None
