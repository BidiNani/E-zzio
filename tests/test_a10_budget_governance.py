"""
tests/test_a10_budget_governance.py — Acceptance Test Suite for Phase A10 Budget & Cost Governance.
Tests:
- budget available (successful preflight)
- budget exhausted (fail-closed preflight rejection)
- token budget exceeded (fail-closed)
- call budget exceeded (fail-closed)
- unknown provider cost (marks 'UNKNOWN', never 0.0)
- local zero-cost provider (evaluates to 0.0 only when strictly known)
- rollback/failure accounting
- retry accounting
- mission summary aggregation
"""
import pytest

from core.governance.budget_governor import BudgetGovernor, BudgetRecord


def test_a10_1_budget_available_and_reservation():
    gov = BudgetGovernor(mission_budget_limit=5.0, max_calls_per_mission=10)
    pre = gov.preflight("m1", "t1", "google", "gemini-2.5-flash", estimated_tokens=500)

    assert pre.allowed is True
    assert pre.reason == "ALLOWED"
    assert pre.reservation_id is not None
    assert pre.remaining_budget == 5.0

    rec = gov.postflight(
        reservation_id=pre.reservation_id,
        mission_id="m1",
        task_id="t1",
        provider="google",
        model="gemini-2.5-flash",
        worker="native",
        input_tokens=1000,
        output_tokens=500,
        latency_ms=120.0,
    )
    assert isinstance(rec, BudgetRecord)
    assert isinstance(rec.actual_cost, float)
    assert rec.actual_cost > 0.0
    assert rec.budget_remaining < 5.0


def test_a10_2_budget_exhausted_fail_closed():
    gov = BudgetGovernor(mission_budget_limit=0.001)

    # Exhaust budget with expensive call
    gov.postflight(
        reservation_id=None,
        mission_id="m-exhaust",
        task_id="t0",
        provider="google",
        model="gemini-2.5-pro",
        worker="native",
        input_tokens=10_000,
        output_tokens=5_000,
        latency_ms=2000.0,
    )

    # Next call must fail-closed
    pre = gov.preflight("m-exhaust", "t1", "google", "gemini-2.5-flash", estimated_tokens=100)
    assert pre.allowed is False
    assert "[FAIL-CLOSED]" in pre.reason
    assert "budget exhausted" in pre.reason


def test_a10_3_token_budget_exceeded():
    gov = BudgetGovernor(max_tokens_per_mission=10_000)

    # Use 9,000 tokens
    gov.postflight(
        reservation_id=None,
        mission_id="m-tokens",
        task_id="t0",
        provider="google",
        model="gemini-2.5-flash",
        input_tokens=5000,
        output_tokens=4000,
    )

    # Preflight requesting 2,000 tokens exceeds 10,000 bound -> Fail-closed
    pre = gov.preflight("m-tokens", "t1", "google", "gemini-2.5-flash", estimated_tokens=2000)
    assert pre.allowed is False
    assert "token budget exceeded" in pre.reason


def test_a10_4_call_budget_exceeded():
    gov = BudgetGovernor(max_calls_per_mission=2)

    gov.postflight(None, "m-calls", "t1", "google", "gemini-2.5-flash")
    gov.postflight(None, "m-calls", "t2", "google", "gemini-2.5-flash")

    # 3rd call must be rejected
    pre = gov.preflight("m-calls", "t3", "google", "gemini-2.5-flash")
    assert pre.allowed is False
    assert "call budget exceeded" in pre.reason


def test_a10_5_unknown_provider_cost_not_zero():
    gov = BudgetGovernor()
    rec = gov.postflight(
        reservation_id=None,
        mission_id="m-unknown",
        task_id="t1",
        provider="unregistered_provider",
        model="custom-neural-model-xyz",
        input_tokens=2000,
        output_tokens=1000,
    )

    # HARD INVARIANT: Unknown model cost is "UNKNOWN", NEVER 0.0
    assert rec.actual_cost == "UNKNOWN"
    assert rec.estimated_cost == "UNKNOWN"


def test_a10_6_local_zero_cost_provider():
    gov = BudgetGovernor()
    rec = gov.postflight(
        reservation_id=None,
        mission_id="m-local",
        task_id="t1",
        provider="ollama",
        model="qwen2.5-coder:7b",
        input_tokens=5000,
        output_tokens=2000,
    )

    # Local Ollama model is known to have 0.0 monetary cost
    assert rec.actual_cost == 0.0
    assert rec.estimated_cost == 0.0


def test_a10_7_rollback_and_failure_accounting():
    gov = BudgetGovernor()
    rec = gov.postflight(
        reservation_id=None,
        mission_id="m-fail",
        task_id="t1",
        provider="google",
        model="gemini-2.5-flash",
        input_tokens=1500,
        output_tokens=300,
        is_rollback=True,
    )

    assert rec.is_rollback is True
    # Rollback still consumes tokens and budget
    assert rec.total_tokens == 1800
    assert isinstance(rec.actual_cost, float)


def test_a10_8_retry_accounting_and_summary_aggregation():
    gov = BudgetGovernor(mission_budget_limit=10.0)

    # Call 1: attempt 1 (failed)
    gov.postflight(
        None, "m-summary", "t1", "google", "gemini-2.5-flash",
        input_tokens=1000, output_tokens=200, latency_ms=100.0, is_retry=False,
    )
    # Call 2: retry attempt 2
    gov.postflight(
        None, "m-summary", "t1", "google", "gemini-2.5-flash",
        input_tokens=1000, output_tokens=400, latency_ms=150.0, is_retry=True,
    )
    # Call 3: local helper
    gov.postflight(
        None, "m-summary", "t2", "ollama", "qwen2.5-coder:7b",
        input_tokens=500, output_tokens=100, latency_ms=50.0,
    )

    summary = gov.get_mission_summary("m-summary")
    assert summary["mission_id"] == "m-summary"
    assert summary["total_calls"] == 3
    assert summary["cloud_calls"] == 2
    assert summary["local_calls"] == 1
    assert summary["total_tokens"] == 3200
    assert summary["total_latency_ms"] == 300.0
    assert summary["provider_usage"]["google"] == 2
    assert summary["provider_usage"]["ollama"] == 1
    assert isinstance(summary["estimated_monetary_cost"], float)
    assert summary["budget_remaining"] < 10.0
