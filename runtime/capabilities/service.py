from typing import Optional, Dict, Any
from runtime.capabilities.lifecycle import CapabilityState
from runtime.capabilities.validator import CapabilityValidator
from runtime.capabilities.expiry import CapabilityExpiryManager
from runtime.capabilities.revocation import CapabilityRevocationRegistry
from runtime.capabilities.audit import CapabilityAuditBridge
from runtime.execution.context import ExecutionContext
from runtime.execution.state import ExecutionState

class CapabilityEnforcementGateway:
    """
    Unified gateway orchestrating validation, expiry, revocation, 
    and audit for capability tokens.
    """
    def __init__(self, revocation_registry: Optional[CapabilityRevocationRegistry] = None):
        self.revocation_registry = revocation_registry or CapabilityRevocationRegistry()
        self.audit_bridge = CapabilityAuditBridge()

    def validate_capability(self, token_id: str, token_meta: Dict[str, Any]) -> bool:
        """
        Enforces complete capability validation checks.
        """
        if self.revocation_registry.is_revoked(token_id):
            CapabilityAuditBridge.record_transition(token_id, token_meta.get("state", "UNKNOWN"), CapabilityState.REVOKED)
            return False

        if CapabilityExpiryManager.check_expiry(token_meta):
            CapabilityAuditBridge.record_transition(token_id, token_meta.get("state", "UNKNOWN"), CapabilityState.EXPIRED)
            return False

        return CapabilityValidator.is_valid(token_meta)

    def authorize_execution(self, context: ExecutionContext, token_meta: Dict[str, Any]) -> bool:
        """
        Authorizes execution context via capability enforcement.
        """
        if not context.has_capability():
            context.state = ExecutionState.BLOCKED
            return False

        is_valid = self.validate_capability(context.capability_id, token_meta)
        if not is_valid:
            context.state = ExecutionState.EXPIRED
            return False

        context.state = ExecutionState.AUTHORIZED
        return True

    def revoke_capability(self, token_id: str, token_meta: Dict[str, Any]):
        """
        Irrevocably revokes a capability token and logs the event.
        """
        self.revocation_registry.revoke(token_id)
        CapabilityAuditBridge.record_transition(token_id, token_meta.get("state", "UNKNOWN"), CapabilityState.REVOKED)
