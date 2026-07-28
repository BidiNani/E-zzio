from typing import Dict, Any, Optional
from runtime.audit import AuditBridge, AuditAction
from runtime.capabilities.service import CapabilityEnforcementGateway

class MemoryPolicyEngine:
    """
    Enforces strict security policies on memory operations.
    Rule: No memory operation without a valid capability and audit trail.
    """
    def __init__(self, capability_gateway: Optional[CapabilityEnforcementGateway] = None):
        self.capability_gateway = capability_gateway or CapabilityEnforcementGateway()

    def authorize_write(self, capability_id: Optional[str], token_meta: Dict[str, Any], session_id: str) -> bool:
        """
        Authorizes and audits a memory write operation.
        """
        if not capability_id:
            AuditBridge.emit(
                component="MemoryGateway",
                action=AuditAction.MEMORY_WRITE,
                capability_id=None,
                status="BLOCKED",
                metadata={"reason": "no_capability_provided", "session_id": session_id}
            )
            return False

        is_valid = self.capability_gateway.validate_capability(capability_id, token_meta)
        if not is_valid:
            AuditBridge.emit(
                component="MemoryGateway",
                action=AuditAction.MEMORY_WRITE,
                capability_id=capability_id,
                status="EXPIRED",
                metadata={"reason": "invalid_or_expired_capability", "session_id": session_id}
            )
            return False

        AuditBridge.emit(
            component="MemoryGateway",
            action=AuditAction.MEMORY_WRITE,
            capability_id=capability_id,
            status="SUCCESS",
            metadata={"session_id": session_id}
        )
        return True

    def authorize_read(self, capability_id: Optional[str], token_meta: Dict[str, Any], session_id: str) -> bool:
        """
        Authorizes and audits a memory read operation.
        """
        if not capability_id:
            AuditBridge.emit(
                component="MemoryGateway",
                action=AuditAction.MEMORY_READ,
                capability_id=None,
                status="BLOCKED",
                metadata={"reason": "no_capability_provided", "session_id": session_id}
            )
            return False

        is_valid = self.capability_gateway.validate_capability(capability_id, token_meta)
        if not is_valid:
            AuditBridge.emit(
                component="MemoryGateway",
                action=AuditAction.MEMORY_READ,
                capability_id=capability_id,
                status="EXPIRED",
                metadata={"reason": "invalid_or_expired_capability", "session_id": session_id}
            )
            return False

        AuditBridge.emit(
            component="MemoryGateway",
            action=AuditAction.MEMORY_READ,
            capability_id=capability_id,
            status="SUCCESS",
            metadata={"session_id": session_id}
        )
        return True
