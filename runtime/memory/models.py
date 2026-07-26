from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import uuid

@dataclass(frozen=True)
class MemoryItem:
    """
    Standardized, immutable memory record.
    Carries session correlation, content payload, and capability provenance.
    """
    memory_id: str = field(default_factory=lambda: f"mem_{uuid.uuid4().hex[:8]}")
    session_id: str = "default"
    content: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    capability_id: Optional[str] = None
    audit_id: Optional[str] = None
