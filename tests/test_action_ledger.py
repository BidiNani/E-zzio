import pytest
from runtime.action.contracts import ActionContract
from runtime.action.registry import ActionRegistry
from runtime.action.store import ActionStore

def test_action_execution_ledger_persistence(tmp_path):
    db_file = str(tmp_path / "test_action_ledger.db")
    store = ActionStore(db_path=db_file)
    registry = ActionRegistry(store=store)

    contract = ActionContract(
        name="NOTIFY_USER",
        description="Notify user",
        permission="notification.send",
        cost=2,
        schema={"message": "str"}
    )

    registry.register(contract, lambda p: {"sent": True, "msg": p["message"]})

    # Test 1: Succès
    registry.execute("NOTIFY_USER", {"message": "Hello"}, active_permissions=["notification.send"])
    
    # Test 2: Permission bloquée
    registry.execute("NOTIFY_USER", {"message": "Blocked msg"}, active_permissions=[])

    history = store.get_execution_history(action_name="NOTIFY_USER")
    
    assert len(history) == 2
    assert history[0]["status"] == "BLOCKED"  # Le plus récent d'abord
    assert history[0]["payload"]["message"] == "Blocked msg"
    
    assert history[1]["status"] == "SUCCESS"
    assert history[1]["cost"] == 2

def test_action_execution_ledger_error(tmp_path):
    db_file = str(tmp_path / "test_action_ledger_error.db")
    store = ActionStore(db_path=db_file)
    registry = ActionRegistry(store=store)

    contract = ActionContract(name="FAIL_ACTION", description="Fails", permission="*")
    
    def failing_handler(payload):
        raise ValueError("Simulated crash")
        
    registry.register(contract, failing_handler)
    registry.execute("FAIL_ACTION", {}, active_permissions=["*"])
    
    history = store.get_execution_history()
    assert len(history) == 1
    assert history[0]["status"] == "ERROR"
    assert "Simulated crash" in history[0]["result"]["error"]
