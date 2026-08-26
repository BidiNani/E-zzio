import time
import uuid
import threading
from typing import List, Optional, Callable, Dict, Any
from v17.events.models import ProductEvent, EventSeverity
from v17.sanitization.sanitizer import sanitize_data

class EventBuffer:
    def __init__(self, max_size: int = 500):
        self.max_size = max_size
        self._events: List[ProductEvent] = []
        self._subscribers: List[Callable[[ProductEvent], None]] = []
        self._lock = threading.Lock()

    def publish(
        self,
        event_type: str,
        source: str,
        payload: Dict[str, Any],
        severity: EventSeverity = EventSeverity.INFO,
        correlation_id: Optional[str] = None,
        event_id: Optional[str] = None
    ) -> ProductEvent:
        clean_payload = sanitize_data(payload)
        evt = ProductEvent(
            event_id=event_id or f"evt_{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            source=source,
            severity=severity,
            correlation_id=correlation_id,
            payload=clean_payload
        )
        with self._lock:
            if len(self._events) >= self.max_size:
                self._events.pop(0) # FIFO eviction
            self._events.append(evt)
            subscribers = list(self._subscribers)

        for sub in subscribers:
            try:
                sub(evt)
            except Exception:
                pass
        return evt

    def get_recent(self, limit: int = 50) -> List[ProductEvent]:
        with self._lock:
            safe_limit = min(max(1, limit), self.max_size)
            return list(reversed(self._events[-safe_limit:]))

    def subscribe(self, callback: Callable[[ProductEvent], None]):
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[ProductEvent], None]):
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def clear(self):
        with self._lock:
            self._events.clear()

global_event_buffer = EventBuffer(max_size=500)
