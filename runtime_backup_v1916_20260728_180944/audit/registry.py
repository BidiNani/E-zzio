from typing import List, Optional
from runtime.audit.schema import AuditEvent

class AuditRegistry:
    def __init__(self):
        self._events: List[AuditEvent] = []

    def record(self, event: AuditEvent) -> AuditEvent:
        self._events.append(event)
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
