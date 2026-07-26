from dataclasses import replace
from runtime.contracts.capability import CapabilityToken, TokenSigner
from runtime.policy.engine import PolicyEngine
from runtime.security.guard import SecurityGuard

def test_crypto_and_capability_flow():
    signer = TokenSigner()
    token = CapabilityToken(subject="test-agent", permissions=frozenset(["read", "execute"]))
    sig = signer.sign(token)
    signed_token = replace(token, signature=sig)
    
    assert signer.verify(signed_token) is True
    assert signed_token.allows("read") is True
    assert signed_token.allows("admin") is False
    print("[+] test_crypto_and_capability_flow PASSED")

def test_security_guard_bridge():
    guard = SecurityGuard()
    assert guard.check_permission("unknown-subject", "admin") is False
    print("[+] test_security_guard_bridge PASSED")

if __name__ == "__main__":
    test_crypto_and_capability_flow()
    test_security_guard_bridge()
    print("ALL ARCHITECTURAL INVARIANTS PASSED SUCCESSFULLY")





def test_audit_immutability():
    """Vérifie que l'objet AuditEvent est frozen (immuable) avec FrozenInstanceError."""
    import pytest
    from dataclasses import FrozenInstanceError
    from runtime.audit import AuditEvent
    event = AuditEvent(component="Test", action="TEST_ACTION")
    with pytest.raises(FrozenInstanceError):
        event.status = "TAMPERED"

def test_capability_audit_trace():
    """Vérifie que les actions de la passerelle génèrent des traces dans l'AuditRegistry."""
    from runtime.capabilities.service import CapabilityEnforcementGateway
    from runtime.execution.context import ExecutionContext
    from runtime.audit import AuditBridge
    
    registry = AuditBridge.get_registry()
    registry.clear()
    
    gateway = CapabilityEnforcementGateway()
    context = ExecutionContext(
        execution_id="exec_test_001",
        session_id="session_01",
        capability_id=None,
        tool_request={"action": "read"}
    )
    
    gateway.authorize_execution(context, {})
    
    events = registry.query(execution_id="exec_test_001")
    assert len(events) > 0
    assert events[0].status == "BLOCKED"
    assert events[0].action == "EXECUTION_BLOCKED"


def test_memory_gateway_full_authorized_flow():
    """Vérifie le flux complet d'écriture/lecture mémoriel avec autorisation."""
    from runtime.memory import MemoryGateway
    from runtime.audit import AuditBridge

    registry = AuditBridge.get_registry()
    registry.clear()

    gateway = MemoryGateway()

    # Simulation d'un token valide
    token_meta = {"state": "ACTIVE"}

    # Écriture
    item = gateway.write_memory(
        session_id="session_test",
        content={"key": "value"},
        capability_id="cap_valid_01",
        token_meta=token_meta
    )

    assert item is not None
    assert item.session_id == "session_test"

    # Lecture
    read_item = gateway.read_memory(
        memory_id=item.memory_id,
        capability_id="cap_valid_01",
        token_meta=token_meta,
        session_id="session_test"
    )

    assert read_item is not None
    assert read_item.content == {"key": "value"}

    # Vérification des traces d'audit émanant de la passerelle
    events = registry.query(capability_id="cap_valid_01")
    assert len(events) >= 2
