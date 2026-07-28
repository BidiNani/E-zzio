from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import uuid

@dataclass
class AuditEvent:
    event_id: str = field(default_factory=lambda: f"audit_{uuid.uuid4().hex[:8]}")
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    component: str = "Unknown"
    action: str = "UNKNOWN_ACTION"
    status: str = "SUCCESS"
    execution_id: Optional[str] = None
    capability_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
