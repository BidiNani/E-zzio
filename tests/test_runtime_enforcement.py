import pytest
import os
from runtime.action.contracts import ActionContract, RiskLevel
from runtime.action.registry import ActionRegistry
from runtime.action.context import ExecutionContext, get_hmac_secret
from runtime.action.state import ExecutionState, validate_transition
from runtime.action.store import ActionStore

def dummy_handler(ctx: ExecutionContext, payload: dict):
    return {"processed": True, "val": payload.get("val")}

def test_context_mutation_invalidates_signature():
    """Vérifie qu'une altération manuelle des champs du contexte corrompt immédiatement le HMAC."""
    ctx = ExecutionContext(trace_id="tr_secure_01", budget_remaining=100)
    assert ctx.verify_signature() is True

    corrupted_ctx = replace_field_unsafe(ctx, budget_remaining=999)
    assert corrupted_ctx.verify_signature() is False

def replace_field_unsafe(obj, **kwargs):
    data = obj.to_dict()
    data.update(kwargs)
    return ExecutionContext(
        trace_id=data["trace_id"],
        parent_trace_id=data["parent_trace_id"],
        agent_id=data["agent_id"],
        permissions=tuple(data["permissions"]),
        budget_remaining=data["budget_remaining"],
        signature=data["signature"],
        metadata=data["metadata"]
    )

def test_production_hmac_missing_env(monkeypatch):
    """Vérifie qu'une exception critique est levée si le secret HMAC manque en production (sans ligne morte)."""
    monkeypatch.setenv("EZZIO_ENV", "production")
    monkeypatch.delenv("EZZIO_HMAC_SECRET", raising=False)
    
    with pytest.raises(RuntimeError, match="CRITICAL: EZZIO_HMAC_SECRET is missing"):
        get_hmac_secret()

def test_registry_active_state_machine_flow(tmp_path):
    """Vérifie que le registre applique activement la State Machine et trace les transitions dans SQLite."""
    db_file = str(tmp_path / "test_state_ledger.db")
    store = ActionStore(db_path=db_file)
    registry = ActionRegistry(store=store)

    contract = ActionContract(name="STATE_TEST", description="State test", permission="*")
    registry.register(contract, dummy_handler)

    res = registry.execute("STATE_TEST", {"val": "ok"})
    assert res["status"] == "SUCCESS"

    # Vérification que les transitions ont été consignées en base
    with sqlite3.connect(db_file) as conn:
        cursor = conn.execute("SELECT from_state, to_state FROM state_transitions") if hasattr(sqlite3.Connection, "executings") else conn.execute("SELECT from_state, to_state FROM state_transitions")
        transitions = cursor.fetchall()
        
    assert len(transitions) >= 4  # CREATED -> VALIDATING -> AUTHORIZED -> RUNNING -> SUCCESS
