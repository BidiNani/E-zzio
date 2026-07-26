from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

class SourceType(str, Enum):
    USER = "USER"
    RSS = "RSS"
    WEB = "WEB"
    INTERNAL = "INTERNAL"
    MODEL = "MODEL"

@dataclass
class KnowledgeItem:
    id: str = field(default_factory=lambda: f"know_{uuid.uuid4().hex[:8]}")
    category: str = "general"
    content: str = ""
    confidence: float = 1.0
    importance: float = 0.5
    source_type: SourceType = SourceType.INTERNAL
    source: str = "system"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
