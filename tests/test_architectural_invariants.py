import pytest

def test_capability_permissions():
    """Vérifie le contrôle des permissions simples et l'état de la capacité."""
    from runtime.capabilities.models import Capability

    cap = Capability(name="file_system", permissions=["read", "write"], enabled=True)

    assert cap.allows("read") is True
    assert cap.allows("execute") is False

    cap.enabled = False
    assert cap.allows("read") is False

def test_audit_log_emission():
    """Vérifie que les événements d'audit sont enregistrés de façon claire et lisible."""
    from runtime.audit import AuditBridge

    registry = AuditBridge.get_registry()
    registry.clear()

    e1 = AuditBridge.emit("TestComponent", "ACTION_EXECUTE", status="SUCCESS", metadata={"target": "file.txt"})
    events = registry.query()

    assert len(events) == 1
    assert events[0].component == "TestComponent"
    assert events[0].metadata["target"] == "file.txt"

def test_capability_audit_trace():
    """Vérifie le blocage et la traçabilité lors d'une exécution non autorisée."""
    from runtime.capabilities.service import CapabilityEnforcementGateway
    from runtime.execution.context import ExecutionContext
    from runtime.audit import AuditBridge

    registry = AuditBridge.get_registry()
    registry.clear()

    gateway = CapabilityEnforcementGateway()
    context = ExecutionContext(
        execution_id="exec_001",
        session_id="session_01",
        capability_id=None,
        tool_request={"action": "read"}
    )

    gateway.authorize_execution(context, {})
    events = registry.query(execution_id="exec_001")
    assert len(events) > 0
    assert events[0].status == "BLOCKED"

def test_memory_gateway_write_and_read():
    """Vérifie le flux écriture/lecture en mémoire avec contrôle d'accès."""
    from runtime.memory import MemoryGateway
    from runtime.audit import AuditBridge

    registry = AuditBridge.get_registry()
    registry.clear()

    gateway = MemoryGateway()
    token_meta = {"id": "cap_memory_01", "state": "ACTIVE"}

    item = gateway.write_memory(
        session_id="session_test",
        content={"user_pref": "dark_mode"},
        capability_id="cap_memory_01",
        token_meta=token_meta
    )
    assert item is not None

    read_item = gateway.read_memory(
        memory_id=item.memory_id,
        capability_id="cap_memory_01",
        token_meta=token_meta
    )
    assert read_item is not None
    assert read_item.content["user_pref"] == "dark_mode"

def test_sqlite_ttl_maintenance_purge():
    """Vérifie la purge contrôlée des éléments expirés en mémoire via SQLite."""
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
        content={"temp": "data"},
        capability_id="cap_1",
        token_meta=token_meta,
        ttl_seconds=0.01
    )

    time.sleep(0.02)
    purged_ids = gateway.run_maintenance()

    assert item.memory_id in purged_ids
    assert gateway.store.read(item.memory_id) is None
    expiry_store.clear()
