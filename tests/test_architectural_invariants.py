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
    token_meta = {"id": "cap_valid_01", "state": "ACTIVE", "permissions": ["memory.read", "memory.write"], "expires_at": 9999999999}

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


def test_audit_hash_chain_integrity():
    """Vérifie que le chaînage cryptographique des événements d'audit est incassable."""
    from runtime.audit import AuditBridge
    registry = AuditBridge.get_registry()
    registry.clear()
    
    e1 = AuditBridge.emit("Test", "ACT_1")
    e2 = AuditBridge.emit("Test", "ACT_2")
    e3 = AuditBridge.emit("Test", "ACT_3")
    
    assert e1.current_hash is not None
    assert e2.previous_hash == e1.current_hash
    assert e3.previous_hash == e2.current_hash

def test_memory_content_hash_integrity():
    """Vérifie le checksum SHA-256 de la mémoire."""
    from runtime.memory.models import MemoryItem
    item1 = MemoryItem(content={"directive": "protect"})
    item2 = MemoryItem(content={"directive": "protect"})
    item_diff = MemoryItem(content={"directive": "destroy"})
    
    assert item1.content_hash == item2.content_hash
    assert item1.content_hash != item_diff.content_hash

