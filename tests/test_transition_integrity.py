import pytest
from runtime.action.contracts import ActionContract
from runtime.action.registry import ActionRegistry
from runtime.action.context import ExecutionContext
from runtime.action.store import ActionStore

def dummy_handler(ctx: ExecutionContext, payload: dict):
    return {"status": "ok", "value": payload.get("value")}

def test_full_execution_chain_is_persisted(tmp_path):
    """Vérifie l'intégrité de la chaîne complète des transitions d'états enregistrées en base SQLite."""
    db_file = str(tmp_path / "ledger_chain.db")
    store = ActionStore(db_path=db_file)
    registry = ActionRegistry(store=store)

    contract = ActionContract(
        name="CHAIN_TEST",
        description="Full chain integration test",
        permission="*"
    )
    registry.register(contract, dummy_handler)

    result = registry.execute("CHAIN_TEST", {"value": 42})
    assert result["status"] == "SUCCESS"

    # Récupération de l'exec_id depuis l'historique d'exécution
    history = store.get_execution_history(action_name="CHAIN_TEST")
    assert len(history) == 1
    exec_id = history[0]["exec_id"]

    # Vérification séquentielle exacte de la chaîne d'états dans state_transitions
    transitions = store.get_transition_history(exec_id)
    assert transitions == [
        ("CREATED", "VALIDATING"),
        ("VALIDATING", "AUTHORIZED"),
        ("AUTHORIZED", "RUNNING"),
        ("RUNNING", "SUCCESS")
    ]
