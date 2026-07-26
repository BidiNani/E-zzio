from typing import List, Optional
import hashlib
import json
from runtime.audit.schema import AuditEvent

class AuditRegistry:
    def __init__(self):
        self._events: List[AuditEvent] = []
        self._last_hash = "GENESIS"

    def get_last_hash(self) -> str:
        return self._last_hash

    def record(self, event: AuditEvent) -> AuditEvent:
        payload = {
            "id": event.event_id,
            "time": event.timestamp,
            "component": event.component,
            "action": event.action,
            "execution": event.execution_id,
            "capability": event.capability_id,
            "status": event.status,
            "metadata": event.metadata,
            "previous": self._last_hash
        }
        event_str = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
        current_hash = hashlib.sha256(event_str.encode("utf-8")).hexdigest()
        
        object.__setattr__(event, 'previous_hash', self._last_hash)
        object.__setattr__(event, 'current_hash', current_hash)
        
        self._events.append(event)
        self._last_hash = current_hash
        return event

    def query(self, execution_id: Optional[str] = None, capability_id: Optional[str] = None) -> List[AuditEvent]:
        results = self._events
        if execution_id:
            results = [e for e in results if e.execution_id == execution_id]
        if capability_id:
            results = [e for e in results if e.capability_id == capability_id]
        return results

    def clear(self):
        self._events.clear()
        self._last_hash = "GENESIS"
