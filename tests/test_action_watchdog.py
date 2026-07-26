import time
import pytest
from runtime.action.contracts import ActionContract
from runtime.action.registry import ActionRegistry
from runtime.action.context import ExecutionContext
from runtime.action.store import ActionStore

def slow_handler(ctx: ExecutionContext, payload: dict):
    time.sleep(0.5)
    return {"done": True}

def invalid_signature_handler(a, b, c):
    return {}

def test_tuple_permissions_immutability():
    """Vérifie l'immuabilité réelle de la collection permissions."""
    ctx = ExecutionContext(trace_id="t_tuple", permissions=["read", "write"])
    assert isinstance(ctx.permissions, tuple)
    with pytest.raises(AttributeError):
        ctx.permissions.append("admin")

def test_consume_budget_negative_throw():
    """Vérifie le rejet d'un dépassement de budget."""
    ctx = ExecutionContext(trace_id="t_budget", budget_remaining=10)
    with pytest.raises(ValueError, match="Execution budget exceeded"):
        ctx.consume_budget(15)

def test_invalid_handler_signature():
    """Vérifie l'interception des handlers à arité incorrecte."""
    registry = ActionRegistry()
    contract = ActionContract(name="BAD_SIG", description="Bad signature", permission="*")
    registry.register(contract, invalid_signature_handler)

    res = registry.execute("BAD_SIG", {})
    assert res["status"] == "ERROR"
    assert "Handler signature unsupported" in res["error"]

def test_execution_timeout_watchdog(tmp_path):
    """Vérifie le déclenchement du Watchdog et l'enregistrement du statut TIMEOUT."""
    db_file = str(tmp_path / "test_watchdog.db")
    store = ActionStore(db_path=db_file)
    registry = ActionRegistry(store=store)

    # Action configurée avec un timeout ultra-court de 0.1s
    contract = ActionContract(
        name="SLOW_ACTION",
        description="Slow action",
        permission="*",
        timeout=0.1
    )
    registry.register(contract, slow_handler)

    res = registry.execute("SLOW_ACTION", {})

    assert res["status"] == "TIMEOUT"
    assert "timed out after 0.1s" in res["error"]

    # Vérification de l'enregistrement SQLite
    history = store.get_execution_history(action_name="SLOW_ACTION")
    assert len(history) == 1
    assert history[0]["status"] == "TIMEOUT"
