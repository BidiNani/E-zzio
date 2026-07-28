from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from enum import Enum
import uuid

class MemoryClass(str, Enum):
    TEMPORARY = "TEMPORARY"
    SESSION = "SESSION"
    KNOWLEDGE = "KNOWLEDGE"
    IDENTITY = "IDENTITY"

@dataclass
class MemoryItem:
    memory_id: str = field(default_factory=lambda: f"mem_{uuid.uuid4().hex[:8]}")
    session_id: str = "default"
    memory_class: MemoryClass = MemoryClass.SESSION
    content: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    capability_id: Optional[str] = None
