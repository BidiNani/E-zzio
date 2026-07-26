from dataclasses import dataclass, asdict
from typing import Any, Dict

@dataclass
class ExecutionTrace:
    """Structure d'audit causale (Distributed Tracing Model)."""
    request_id: str
    session_id: str
    runtime_version: str
    capability: Dict[str, Any]
    execution: Dict[str, Any]
    decision: Dict[str, Any]

    def to_dict(self) -> dict:
        return asdict(self)