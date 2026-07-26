import pytest
from dataclasses import FrozenInstanceError
from runtime.action.contracts import ActionContract
from runtime.action.registry import ActionRegistry
from runtime.action.context import ExecutionContext

def v2_handler(ctx: ExecutionContext, payload: dict):
    return {"trace": ctx.trace_id, "val": payload.get("val")}

def legacy_v1_handler(payload: dict):
    return {"legacy_processed": True, "val": payload.get("val")}

def test_context_immutability():
    ctx = ExecutionContext(trace_id="t1", permissions=["read"])
    with pytest.raises(FrozenInstanceError):
        ctx.agent_id = "hacked_agent"

def test_context_validation_invariants():
    # Budget négatif interdit
    with pytest.raises(ValueError, match="cannot be negative"):
        ExecutionContext(trace_id="t_valid", budget_remaining=-10)

    # trace_id vide interdit
    with pytest.raises(ValueError, match="non-empty string"):
        ExecutionContext(trace_id="")

def test_context_serialization_roundtrip():
    original = ExecutionContext(
        trace_id="tr_serial_01",
        parent_trace_id="tr_root",
        agent_id="ezzio-worker",
        permissions=["memory.write"],
        budget_remaining=85,
        metadata={"env": "prod"}
    )
    serialized = original.to_dict()
    hydrated = ExecutionContext.from_dict(serialized)

    assert hydrated == original
    assert hydrated.trace_id == "tr_serial_01"
    assert hydrated.parent_trace_id == "tr_root"

def test_legacy_handler_compatibility():
    registry = ActionRegistry()
    contract = ActionContract(name="LEGACY_ACTION", description="Legacy test", permission="*")
    registry.register(contract, legacy_v1_handler)

    res = registry.execute("LEGACY_ACTION", {"val": "test_v1"})
    assert res["status"] == "SUCCESS"
    assert res["result"]["legacy_processed"] is True

def test_budget_enforcement():
    registry = ActionRegistry()
    contract = ActionContract(name="HEAVY_ACTION", description="Expensive action", permission="*", cost=30)
    registry.register(contract, legacy_v1_handler)

    poor_ctx = ExecutionContext(trace_id="poor", budget_remaining=20)
    res_blocked = registry.execute("HEAVY_ACTION", {"val": "test"}, context=poor_ctx)
    assert res_blocked["status"] == "BLOCKED"
    assert "Insufficient execution budget" in res_blocked["error"]

    rich_ctx = ExecutionContext(trace_id="rich", budget_remaining=100)
    res_ok = registry.execute("HEAVY_ACTION", {"val": "test"}, context=rich_ctx)
    assert res_ok["status"] == "SUCCESS"
    assert res_ok["budget_remaining"] == 70

def test_causal_trace_derivation():
    parent = ExecutionContext(trace_id="parent_001", agent_id="ezzio")
    child = parent.derive_child(child_trace_id="child_002")

    assert child.trace_id == "child_002"
    assert child.parent_trace_id == "parent_001"
    assert child.agent_id == "ezzio"
