import pytest
from runtime.action.contracts import ActionContract
from runtime.action.registry import ActionRegistry

def test_action_contract_validation():
    contract = ActionContract(
        name="TEST_ACTION",
        description="Test contract",
        permission="test.run",
        schema={"content": "str", "score": "float"}
    )

    # Payload valide
    assert contract.validate_payload({"content": "hello", "score": 0.9}) == []

    # Payload invalide
    errors = contract.validate_payload({"content": 123})
    assert len(errors) > 0

def test_action_registry_permissions_and_execution():
    registry = ActionRegistry()
    
    contract = ActionContract(
        name="STORE_KNOWLEDGE",
        description="Store memory",
        permission="memory.write",
        schema={"content": "str"}
    )

    def dummy_handler(payload):
        return {"stored": payload["content"], "saved": True}

    registry.register(contract, dummy_handler)

    # 1. Échec par permission manquante
    res_blocked = registry.execute("STORE_KNOWLEDGE", {"content": "test"}, active_permissions=["other.read"])
    assert res_blocked["status"] == "BLOCKED"

    # 2. Succès avec permission explicite
    res_success = registry.execute("STORE_KNOWLEDGE", {"content": "test"}, active_permissions=["memory.write"])
    assert res_success["status"] == "SUCCESS"
    assert res_success["result"]["stored"] == "test"

    # 3. Succès avec wildcard '*'
    res_wildcard = registry.execute("STORE_KNOWLEDGE", {"content": "admin_test"}, active_permissions=["*"])
    assert res_wildcard["status"] == "SUCCESS"

    # 4. Échec action inconnue
    res_unknown = registry.execute("UNKNOWN_ACTION", {}, active_permissions=["*"])
    assert res_unknown["status"] == "BLOCKED"
