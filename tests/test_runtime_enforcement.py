import pytest
import os
from runtime.action.contracts import ActionContract, RiskLevel
from runtime.action.registry import ActionRegistry
from runtime.action.context import ExecutionContext
from runtime.action.state import ExecutionState, validate_transition

def dummy_handler(ctx: ExecutionContext, payload: dict):
    return {"processed": True, "val": payload.get("val")}

def test_context_mutation_invalidates_signature():
    """Vérifie qu'une altération manuelle des champs du contexte corrompt immédiatement le HMAC."""
    ctx = ExecutionContext(trace_id="tr_secure_01", budget_remaining=100)
    assert ctx.verify_signature() is True

    # Mutation forcée d'un champ protégé via dataclass replace ou altération directe
    corrupted_ctx = replace_field_unsafe(ctx, budget_remaining=999)
    assert corrupted_ctx.verify_signature() is False

def replace_field_unsafe(obj, **kwargs):
    """Utilitaire pour simuler une altération mémoire non signée."""
    data = obj.to_dict()
    data.update(kwargs)
    # On recrée l'objet SANS recalculer la signature pour simuler une attaque/corruption
    return ExecutionContext(
        trace_id=data["trace_id"],
        parent_trace_id=data["parent_trace_id"],
        agent_id=data["agent_id"],
        permissions=tuple(data["permissions"]),
        budget_remaining=data["budget_remaining"],
        signature=data["signature"], # Signature ancienne non mise à jour
        metadata=data["metadata"]
    )

def test_production_hmac_missing_env(monkeypatch):
    """Vérifie qu'une exception critique est levée si le secret HMAC manque en production."""
    monkeypatch.setenv("EZZIO_ENV", "production")
    monkeypatch.delenv("EZZIO_ENV_SECRET", raising=False)
    # Simulation de l'appel de get_hmac_secret en mode prod sans secret
    from runtime.action.context import get_hmac_secret
    # S'assurons que la variable d'environnement EZZIO_HMAC_SECRET est absente
    monkeypatch.delenv("EZZIO_HMAC_SECRET", raising=False)
    
    with pytest.raises(RuntimeError, match="CRITICAL: EZZIO_HMAC_SECRET is missing"):
        get_hmac_secret()

def test_registry_active_state_machine_flow():
    """Vérifie que le registre applique activement le cycle de vie de la State Machine."""
    registry = ActionRegistry()
    contract = ActionContract(name="STATE_TEST", description="State test", permission="*")
    registry.register(contract, dummy_handler)

    res = registry.execute("STATE_TEST", {"val": "ok"})
    assert res["status"] == "SUCCESS"
