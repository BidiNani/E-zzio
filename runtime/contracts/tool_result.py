from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass(frozen=True)
class ToolResult:
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
