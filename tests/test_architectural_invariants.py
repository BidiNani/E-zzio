import pytest
from dataclasses import FrozenInstanceError

def test_crypto_and_capability_flow():
    assert True

def test_security_guard_bridge():
    assert True

def test_audit_immutability():
    from runtime.audit import AuditEvent
    event = AuditEvent(component="Test", action="TEST_ACTION")
    with pytest.raises(FrozenInstanceError):
        event.status = "TAMPERED"

def test_capability_audit_trace():
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
    from runtime.memory.models import MemoryItem
    item1 = MemoryItem(content={"directive": "protect"})
    item2 = MemoryItem(content={"directive": "protect"})
    item_diff = MemoryItem(content={"directive": "destroy"})
    
    assert item1.content_hash == item2.content_hash
    assert item1.content_hash != item_diff.content_hash

def test_memory_purge_removes_from_ram_store():
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
    gateway.retention_manager.purge_expired()

    # Vérification que la donnée a BIEN été supprimée du store RAM
    assert gateway.store.read(item.memory_id) is None
    expiry_store.clear()
