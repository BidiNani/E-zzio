"""
tests/test_a11_local_autonomy.py — Acceptance Test Suite for Phase A11 Local Autonomy.
Tests:
- local available -> local selected
- local unavailable -> canonical fallback with observable event (no silent cloud)
- local timeout / failure -> bounded escalation
- policy blocks local -> policy respected
- budget blocks cloud -> fail-closed
- router remains sole routing authority
- telemetry and cloud calls avoided metric
"""
import pytest

from core.cognition.local_autonomy import LocalAutonomyManager, LocalEscalationEvent
from core.cognition.model_router import ModelRouter


def test_a11_1_local_available_local_selected():
    mgr = LocalAutonomyManager()
    mgr.set_local_availability(True)

    router = ModelRouter(local_autonomy=mgr)
    decision = router.select_engine(
        task_type="coding",
        complexity_score=0.4,
        prefer_local=True,
    )

    assert decision["provider"] == "ollama"
    assert decision["role"] == "LOCAL_AUTONOMOUS"
    assert decision["is_local"] is True


def test_a11_2_local_unavailable_observable_escalation():
    mgr = LocalAutonomyManager()
    mgr.set_local_availability(False)

    router = ModelRouter(local_autonomy=mgr)
    decision = router.select_engine(
        task_type="coding",
        complexity_score=0.4,
        prefer_local=True,
    )

    # Must escalate to canonical cloud provider (Gemini or similar)
    assert decision["provider"] in ("gemini", "groq", "google")
    assert decision["is_local"] is False

    # HARD INVARIANT: Not silent! An observable LOCAL_UNAVAILABLE event must have been recorded
    assert len(mgr.metrics.escalation_events) == 1
    event = mgr.metrics.escalation_events[0]
    assert event["event_type"] == "LOCAL_UNAVAILABLE"
    assert "LOCAL_SERVICE_UNAVAILABLE" in event["reason"]
    assert event["fallback_model"] == decision["model"]


def test_a11_3_policy_blocks_local_respected():
    mgr = LocalAutonomyManager()
    mgr.set_local_availability(True)

    router = ModelRouter(local_autonomy=mgr)
    # Policy explicitly forbids local execution (e.g. strict compliance policy)
    decision = router.select_engine(
        task_type="coding",
        complexity_score=0.4,
        prefer_local=True,
        policy_permits_local=False,
    )

    # Must respect policy and route to cloud
    assert decision["provider"] != "ollama"
    assert len(mgr.metrics.escalation_events) == 1
    assert "POLICY_BLOCKS_LOCAL" in mgr.metrics.escalation_events[0]["reason"]


def test_a11_4_budget_blocks_cloud_fail_closed():
    mgr = LocalAutonomyManager()
    mgr.set_local_availability(False)  # Local is down

    router = ModelRouter(local_autonomy=mgr)
    # Cloud budget is exhausted
    decision = router.select_engine(
        task_type="coding",
        complexity_score=0.4,
        prefer_local=True,
        budget_permits_cloud=False,
    )

    # HARD INVARIANT: FAIL-CLOSED when cloud budget is exhausted and local unavailable
    assert decision.get("status") == "FAIL_CLOSED"
    assert decision.get("error") == "BUDGET_BLOCKS_CLOUD"
    assert decision.get("provider") is None


def test_a11_5_local_metrics_and_cloud_calls_avoided():
    mgr = LocalAutonomyManager()

    # Simulate 3 successful local calls
    mgr.record_execution(provider="ollama", latency_ms=45.0, tokens=1200)
    mgr.record_execution(provider="ollama", latency_ms=50.0, tokens=800)
    mgr.record_execution(provider="ollama", latency_ms=60.0, tokens=1500)

    # Simulate 1 cloud call with escalation
    esc = LocalEscalationEvent(
        event_type="LOCAL_UNAVAILABLE",
        reason="Socket timeout",
        attempted_model="qwen2.5-coder:7b",
        fallback_model="gemini-2.5-flash",
        fallback_provider="gemini",
    )
    mgr.record_execution(provider="gemini", latency_ms=250.0, tokens=2000, escalation_event=esc)

    summary = mgr.metrics.get_summary()
    assert summary["total_calls"] == 4
    assert summary["local_calls"] == 3
    assert summary["cloud_calls"] == 1
    assert summary["cloud_calls_avoided"] == 3
    assert summary["local_call_ratio"] == 0.75
    assert summary["cloud_call_ratio"] == 0.25
    assert summary["fallback_rate"] == 0.25


def test_a11_6_router_remains_sole_authority():
    router = ModelRouter()
    # Canonical routing without local preference remains sovereign and intact
    res_chat = router.select_engine(task_type="chat", complexity_score=0.2)
    assert res_chat["role"] == "FAST_CHAT"
    assert res_chat["provider"] in ("gemini", "groq", "ollama")

    res_master = router.select_engine(task_type="strategic", complexity_score=0.9)
    assert res_master["role"] == "MASTER_STRATEGIC"
