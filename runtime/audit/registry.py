from typing import List, Optional
import hashlib
from runtime.audit.schema import AuditEvent

class AuditRegistry:
    def __init__(self):
        self._events: List[AuditEvent] = []
        self._last_hash = "GENESIS"

    def get_last_hash(self) -> str:
        return self._last_hash

    def record(self, event: AuditEvent) -> AuditEvent:
        # Sécurisation de la chaîne cryptographique
        event_str = f"{event.event_id}{event.timestamp}{event.action}{event.status}{self._last_hash}"
        current_hash = hashlib.sha256(event_str.encode()).hexdigest()
        
        # Injection du hash dans l'instance immuable
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
