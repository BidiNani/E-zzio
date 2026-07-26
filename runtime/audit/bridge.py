from typing import Optional, Dict, Any
from runtime.audit.schema import AuditEvent
from runtime.audit.registry import AuditRegistry

class AuditBridge:
    _registry = AuditRegistry()

    @classmethod
    def emit(
        cls, component: str, action: str,
        execution_id: Optional[str] = None, capability_id: Optional[str] = None,
        status: str = "SUCCESS", metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        event = AuditEvent(
            component=component, action=action,
            execution_id=execution_id, capability_id=capability_id,
            status=status, metadata=metadata or {},
            previous_hash=cls._registry.get_last_hash()
        )
        return cls._registry.record(event)

    @classmethod
    def get_registry(cls) -> AuditRegistry:
        return cls._registry
