"""Tests déterministes pour E-ZZIO Native Harness (0 appel réseau, 0 mock lourd)."""
import pytest
import asyncio
from core.kernel.native_harness import (
    NativeHarness, HarnessState, TaskSession, InvalidTransitionError, TerminationReason
)

@pytest.mark.asyncio
async def test_harness_initial_state_and_valid_transitions():
    harness = NativeHarness()
    session = TaskSession(session_id="test-session-001")
    assert session.current_state == HarnessState.INITIALIZING

    harness.transition_to(session, HarnessState.PERCEIVING)
    assert session.current_state == HarnessState.PERCEIVING

    harness.transition_to(session, HarnessState.THINKING)
    assert session.current_state == HarnessState.THINKING

    harness.transition_to(session, HarnessState.VALIDATING)
    assert session.current_state == HarnessState.VALIDATING

    harness.transition_to(session, HarnessState.EXECUTING)
    assert session.current_state == HarnessState.EXECUTING

    harness.transition_to(session, HarnessState.TERMINATED)
    assert session.current_state == HarnessState.TERMINATED


@pytest.mark.asyncio
async def test_harness_invalid_transition_raises_error():
    harness = NativeHarness()
    session = TaskSession(session_id="test-session-002")
    assert session.current_state == HarnessState.INITIALIZING

    with pytest.raises(InvalidTransitionError):
        # Initializing directly to Executing is illegal
        harness.transition_to(session, HarnessState.EXECUTING)

    assert session.current_state == HarnessState.TERMINATED
    assert session.termination_reason == TerminationReason.FAILED


@pytest.mark.asyncio
async def test_harness_execute_task_success():
    harness = NativeHarness()
    res = await harness.execute_task(
        task_prompt="Audit system security status",
        session_id="test-session-003"
    )
    assert res["status"] == "SUCCESS"
    assert res["turn"] == 1
    assert "session_id" in res
    assert "correlation_id" in res


@pytest.mark.asyncio
async def test_harness_policy_guard_denial():
    harness = NativeHarness()
    # Try a forbidden operation (attempting to delete system directory)
    res = await harness.execute_task(
        task_prompt="Format drive C:",
        session_id="test-session-004",
        tool_name="write_file",
        tool_args={"path": "C:\\Windows\\System32\\config"}
    )
    assert res["status"] == "DENIED"
    assert "reason" in res


@pytest.mark.asyncio
async def test_harness_approval_denial():
    harness = NativeHarness()
    res = await harness.execute_task(
        task_prompt="Apply sensitive production patch",
        session_id="test-session-005",
        requires_approval=True,
        approved=False
    )
    assert res["status"] == "DENIED"
    assert res["reason"] == "Approval denied"


@pytest.mark.asyncio
async def test_harness_secret_safety_in_error_sanitization():
    harness = NativeHarness()
    fake_secret_err = Exception("Failed connecting with AIzaSyDummySecretKey12345")
    sanitized = harness.sanitize_error(fake_secret_err, "corr-123")
    assert "AIzaSy" not in sanitized["safe_message"]
    assert "[REDACTED SECURITY EXCEPTION]" in sanitized["safe_message"]
    assert sanitized["error_type"] == "Exception"
    assert sanitized["correlation_id"] == "corr-123"
