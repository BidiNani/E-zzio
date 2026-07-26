from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import uuid

@dataclass(frozen=True)
class AuditEvent:
    event_id: str = field(default_factory=lambda: f"audit_{uuid.uuid4().hex[:8]}")
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    component: str = "Unknown"
    action: str = "UNKNOWN_ACTION"
    execution_id: Optional[str] = None
    capability_id: Optional[str] = None
    status: str = "SUCCESS"
    metadata: Dict[str, Any] = field(default_factory=dict)
    previous_hash: str = "GENESIS"
    current_hash: Optional[str] = field(default=None, init=False)
