import pytest
from runtime.action.contracts import ActionContract, RiskLevel
from runtime.action.registry import ActionRegistry
from runtime.action.context import ExecutionContext, SecurityError
from runtime.action.store import ActionStore

def simple_handler(ctx: ExecutionContext, payload: dict):
    return {"status": "ok", "processed": payload.get("data")}

def failing_handler(ctx: ExecutionContext, payload: dict):
    raise RuntimeError("Intentional error for circuit breaker")

def test_context_tampering_quarantine():
    """Vérifie le rejet immédiat et la mise en quarantaine d'un contexte falsifié."""
    registry = ActionRegistry()
    contract = ActionContract(name="SECURE_ACT", description="Secure", permission="*")
    registry.register(contract, simple_handler)

    valid_ctx = ExecutionContext(trace_id="t_sec", budget_remaining=50)
    # Falsification manuelle de la signature
    tampered_ctx = ExecutionContext(trace_id="t_sec", budget_remaining=50, signature="fake_sig_123")

    res = registry.execute("SECURE_ACT", {"data": "test"}, context=tampered_ctx)
    assert res["status"] == "QUARANTINED"

def test_dry_run_simulation_mode():
    """Vérifie que le mode Dry Run simule l'action sans exécuter le handler."""
    registry = ActionRegistry()
    contract = ActionContract(name="DELETE_DB", description="High risk", permission="db.write", risk_level=RiskLevel.CRITICAL)
    registry.register(contract, simple_handler)

    res = registry.execute("DELETE_DB", {"data": "all"}, dry_run=True)
    assert res["status"] == "SIMULATED"
    assert res["risk_level"] == "CRITICAL"
    assert res["required_permission"] == "db.write"

def test_circuit_breaker_tripping(tmp_path):
    """Vérifie que le Circuit Breaker passe en OPEN après 3 échecs consécutifs."""
    db_file = str(tmp_path / "test_cb.db")
    store = ActionStore(db_path=db_file)
    registry = ActionRegistry(store=store)

    contract = ActionContract(name="FAIL_ACT", description="Always fails", permission="*")
    registry.register(contract, failing_handler)

    # 3 Échecs consécutifs
    for _ in range(3):
        registry.execute("FAIL_ACT", {})

    # Le 4ème appel doit être bloqué par le Circuit Breaker OPEN
    res = registry.execute("FAIL_ACT", {})
    assert res["status"] == "BLOCKED"
    assert "Circuit breaker OPEN" in res["error"]

def test_evidence_ledger_generation(tmp_path):
    """Vérifie que chaque exécution produit une preuve d'exécution dans SQLite."""
    db_file = str(tmp_path / "test_evidence.db")
    store = ActionStore(db_path=db_file)
    registry = ActionRegistry(store=store)

    contract = ActionContract(name="EVIDENCE_ACT", description="Evidence test", permission="*", risk_level=RiskLevel.MEDIUM)
    registry.register(contract, simple_handler)

    ctx = ExecutionContext(trace_id="trace_ev_01")
    res = registry.execute("EVIDENCE_ACT", {"data": "evidence_data"}, context=ctx)
    assert res["status"] == "SUCCESS"

    evidence_history = store.get_evidence_history()
    assert len(evidence_history) == 1
    assert evidence_history[0]["root_trace_id"] == "trace_ev_01"
    assert evidence_history[0]["risk_level"] == "MEDIUM"
