import pytest
from runtime.action.contracts import ActionContract
from runtime.action.registry import ActionRegistry
from runtime.action.store import ActionStore

def dummy_bootstrap_handler(payload):
    return {"bootstrapped": True, "val": payload.get("val")}

def test_action_registry_bootstrap(tmp_path):
    db_file = str(tmp_path / "test_bootstrap.db")
    store = ActionStore(db_path=db_file)
    
    # 1. Enregistrement initial avec référence textuelle
    registry_1 = ActionRegistry(store=store)
    contract = ActionContract(
        name="BOOTSTRAP_ACTION",
        description="Test bootstrap",
        permission="bootstrap.run",
        handler_ref="tests.test_action_bootstrap:dummy_bootstrap_handler",
        schema={"val": "str"}
    )
    registry_1.register(contract, dummy_bootstrap_handler)
    
    # Simulation d'un redémarrage complet (nouvelle instance de registre connectée au même store)
    registry_2 = ActionRegistry(store=store)
    assert registry_2.get_contract("BOOTSTRAP_ACTION") is None # RAM vide au départ

    # 2. Exécution du Bootstrap
    loaded = registry_2.bootstrap()
    assert loaded == 1
    assert registry_2.get_contract("BOOTSTRAP_ACTION") is not None

    # 3. Test de l'exécution après bootstrap
    res = registry_2.execute("BOOTSTRAP_ACTION", {"val": "active"}, active_permissions=["bootstrap.run"])
    assert res["status"] == "SUCCESS"
    assert res["result"]["bootstrapped"] is True
    assert res["result"]["val"] == "active"
