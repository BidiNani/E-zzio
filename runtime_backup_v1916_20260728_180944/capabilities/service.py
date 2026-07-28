from typing import Optional, Dict, Any
from runtime.capabilities.lifecycle import CapabilityState
from runtime.capabilities.validator import CapabilityValidator
from runtime.capabilities.expiry import CapabilityExpiryManager
from runtime.capabilities.revocation import CapabilityRevocationRegistry
from runtime.execution.context import ExecutionContext
from runtime.execution.state import ExecutionState
from runtime.audit import AuditBridge, AuditAction

class CapabilityEnforcementGateway:
    """
    Unified gateway orchestrating validation, expiry, revocation, 
    and direct AuditBridge integration for capability tokens.
    """
    def __init__(self, revocation_registry: Optional[CapabilityRevocationRegistry] = None):
        self.revocation_registry = revocation_registry or CapabilityRevocationRegistry()

    def validate_capability(self, token_id: str, token_meta: Dict[str, Any]) -> bool:
        """
        Enforces complete capability validation checks with unified audit emission.
        """
        if self.revocation_registry.is_revoked(token_id):
            AuditBridge.emit(
                component="CapabilityGateway",
                action=AuditAction.REVOKE_TOKEN,
                capability_id=token_id,
                status="BLOCKED",
                metadata={"reason": "token_revoked", "old_state": token_meta.get("state", "UNKNOWN")}
            )
            return False

        if CapabilityExpiryManager.check_expiry(token_meta):
            AuditBridge.emit(
                component="CapabilityGateway",
                action=AuditAction.EXPIRE_TOKEN,
                capability_id=token_id,
                status="EXPIRED",
                metadata={"reason": "token_expired", "old_state": token_meta.get("state", "UNKNOWN")}
            )
            return False

        is_valid = CapabilityValidator.is_valid(token_meta)
        if is_valid:
            AuditBridge.emit(
                component="CapabilityGateway",
                action=AuditAction.VALIDATE_TOKEN,
                capability_id=token_id,
                status="SUCCESS"
            )
        return is_valid

    def authorize_execution(self, context: ExecutionContext, token_meta: Dict[str, Any]) -> bool:
        """
        Authorizes execution context via capability enforcement and audit logging.
        """
        if not context.has_capability():
            context.state = ExecutionState.BLOCKED
            AuditBridge.emit(
                component="CapabilityGateway",
                action=AuditAction.EXECUTION_BLOCKED,
                execution_id=context.execution_id,
                status="BLOCKED",
                metadata={"reason": "no_capability"}
            )
            return False

        is_valid = self.validate_capability(context.capability_id, token_meta)
        if not is_valid:
            context.state = ExecutionState.EXPIRED
            AuditBridge.emit(
                component="CapabilityGateway",
                action=AuditAction.EXECUTION_BLOCKED,
                execution_id=context.execution_id,
                capability_id=context.capability_id,
                status="EXPIRED",
                metadata={"reason": "capability_invalid_or_expired"}
            )
            return False

        context.state = ExecutionState.AUTHORIZED
        AuditBridge.emit(
            component="CapabilityGateway",
            action=AuditAction.EXECUTION_AUTHORIZED,
            execution_id=context.execution_id,
            capability_id=context.capability_id,
            status="SUCCESS"
        )
        return True

    def revoke_capability(self, token_id: str, token_meta: Dict[str, Any]):
        """
        Irrevocably revokes a capability token and logs the event via AuditBridge.
        """
        self.revocation_registry.revoke(token_id)
        AuditBridge.emit(
            component="CapabilityGateway",
            action=AuditAction.REVOKE_TOKEN,
            capability_id=token_id,
            status="SUCCESS",
            metadata={"old_state": token_meta.get("state", "UNKNOWN"), "new_state": CapabilityState.REVOKED}
        )
