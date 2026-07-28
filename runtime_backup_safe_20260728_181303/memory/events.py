import uuid
import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Dict, Any, Optional

@dataclass
class RuntimeEvent:
    """Contrat immuable de l'Event Sourcing, héritier de la Trace Causale."""
    event_type: str
    session_id: str
    actor: str
    payload: Dict[str, Any]
    trace_id: str
    confidence: float = 1.0
    source: str = "runtime_bus"
    parent_event: Optional[str] = None
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat() + "Z")

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)