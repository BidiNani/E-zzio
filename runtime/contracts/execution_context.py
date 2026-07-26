from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass(frozen=True)
class ExecutionContext:
    trace_id: str
    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)