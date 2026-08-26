from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class MemoryItem:
    content: str
    id: Optional[str] = None
    category: str = "general"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[str] = None


class MemoryClass:
    GENERAL = "general"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    WORKING = "working"
