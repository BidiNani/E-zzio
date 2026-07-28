from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List

@dataclass
class CognitiveEvent:
    event_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class EventBus:
    """Internal event bus for decoupled component messaging."""
    def __init__(self):
        self._history: List[CognitiveEvent] = []

    def emit(self, event_type: str, payload: Dict[str, Any] = None) -> CognitiveEvent:
        event = CognitiveEvent(event_type=event_type, payload=payload or {})
        self._history.append(event)
        return event

    def get_history(self) -> List[CognitiveEvent]:
        return self._history

    def clear(self):
        self._history.clear()
