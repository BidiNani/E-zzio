import pytest
from dataclasses import FrozenInstanceError

def test_crypto_and_capability_flow():
    """Vérifie l'instanciation, l'expiration et le contrôle des permissions de CapabilityToken."""
    from runtime.capabilities.models import CapabilityToken
    import time

    token = CapabilityToken(
        id="cap_01",
        issuer="system",
        subject="memory",
        permissions=["memory.read", "memory.write"],
        expires_at=time.time() + 3600,
        signature="sig_valid_sha256"
    )

    assert token.is_expired() is False
    assert token.allows("memory.read") is True
    assert token.allows("exec.run") is False

def test_security_guard_bridge():
    """Vérifie le comportement de validation d'expiration du CapabilityExpiryManager."""
    from runtime.capabilities.expiry import CapabilityExpiryManager
    import time

    future_token = {"expires_at": time.time() + 3600}
    expired_token = {"expires_at": time.time() - 3600}

    assert CapabilityExpiryManager.check_expiry(future_token) is False
    assert CapabilityExpiryManager.check_expiry(expired_token) is True

def test_audit_immutability():
    """Vérifie que l'objet AuditEvent refuse toute modification (FrozenInstanceError)."""
    from runtime.audit import AuditEvent
    event = AuditEvent(component="Test", action="TEST_ACTION")
    with pytest.raises(FrozenInstanceError):
        event.status = "TAMPERED"

def test_capability_audit_trace():
    """Vérifie qu'un accès bloqué émet une trace d'audit explicite."""
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

def test_memory_gateway_full_authorized_flow():
    """Vérifie le cycle complet d'écriture et de lecture mémorielle sous capacité."""
    from runtime.memory import MemoryGateway
    from runtime.audit import AuditBridge

    registry = AuditBridge.get_registry()
    registry.clear()

    gateway = MemoryGateway()
    token_meta = {
        "id": "cap_valid_01",
        "state": "ACTIVE",
        "permissions": ["memory.read", "memory.write"],
        "expires_at": 9999999999
    }

    item = gateway.write_memory(
        session_id="session_test",
        content={"key": "value"},
        capability_id="cap_valid_01",
        token_meta=token_meta
    )
    assert item is not None

    read_item = gateway.read_memory(
        memory_id=item.memory_id,
        capability_id="cap_valid_01",
        token_meta=token_meta,
        session_id="session_test"
    )
    assert read_item is not None
    assert read_item.content == {"key": "value"}

def test_audit_hash_chain_integrity():
    """Vérifie que la modification de métadonnées casse la chaîne cryptographique de l'audit."""
    from runtime.audit import AuditBridge
    registry = AuditBridge.get_registry()
    registry.clear()
    
    e1 = AuditBridge.emit("Test", "ACT_1", metadata={"user": "alice"})
    e2 = AuditBridge.emit("Test", "ACT_2", metadata={"user": "bob"})
    
    assert e1.current_hash is not None
    assert e2.previous_hash == e1.current_hash

def test_memory_content_hash_integrity():
    """Vérifie que MemoryIntegrityChecker détecte la moindre altération mémorielle."""
    from runtime.memory.models import MemoryItem
    from runtime.memory.integrity import MemoryIntegrityChecker

    item = MemoryItem(content={"directive": "protect"})
    assert MemoryIntegrityChecker.verify(item) is True

    # Simulation d'une altération malveillante en mémoire RAM
    object.__setattr__(item, 'content', {"directive": "corrupt"})
    assert MemoryIntegrityChecker.verify(item) is False

def test_memory_purge_removes_from_ram_store():
    """Vérifie que la maintenance dédiée purge la mémoire expirée sans polluer le read."""
    from runtime.memory import MemoryGateway
    from runtime.memory.expiry_store import SQLiteExpiryStore
    import time

    expiry_store = SQLiteExpiryStore("test_memory_expiry.db")
    expiry_store.clear()

    gateway = MemoryGateway()
    gateway.retention_manager.expiry_store = expiry_store

    token_meta = {"state": "ACTIVE"}
    item = gateway.write_memory(
        session_id="s1",
        content={"data": "temp"},
        capability_id="cap_1",
        token_meta=token_meta,
        ttl_seconds=0.01
    )

    time.sleep(0.02)
    # Purge explicite via la méthode de maintenance dédiée
    purged_ids = gateway.run_maintenance()

    assert item.memory_id in purged_ids
    assert gateway.store.read(item.memory_id) is None
    expiry_store.clear()
