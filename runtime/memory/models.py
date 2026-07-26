from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from enum import Enum
import uuid
import hashlib
import json

class MemoryClass(str, Enum):
    TEMPORARY = "TEMPORARY"
    SESSION = "SESSION"
    KNOWLEDGE = "KNOWLEDGE"
    IDENTITY = "IDENTITY"

@dataclass(frozen=True)
class MemoryItem:
    memory_id: str = field(default_factory=lambda: f"mem_{uuid.uuid4().hex[:8]}")
    session_id: str = "default"
    memory_class: MemoryClass = MemoryClass.SESSION
    content: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    capability_id: Optional[str] = None
    audit_id: Optional[str] = None
    content_hash: str = field(init=False)

    def __post_init__(self):
        content_str = json.dumps(
            self.content,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str
        )
        object.__setattr__(self, 'content_hash', hashlib.sha256(content_str.encode("utf-8")).hexdigest())
