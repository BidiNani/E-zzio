"""Tests déterministes pour E-ZZIO Native Harness (0 appel réseau, 0 mock lourd)."""
import asyncio
import sys

import pytest

from core.kernel.native_harness import (
    HarnessState,
    InvalidTransitionError,
    NativeHarness,
    TaskSession,
    TerminationReason,
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


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="Test Windows-only : le PolicyGuard reconnait les chemins systeme Windows (C:\\Windows\\System32). Sur Linux, le chemin est relatif et n'est pas bloque.",
)
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


@pytest.mark.asyncio
async def test_harness_mission_profile_propagation(monkeypatch):
    """Vérifie que mission_profile est converti en minuscules et transmis comme task_type à ModelRouter."""
    harness = NativeHarness()
    recorded_calls = []

    def mock_select_engine(task_type, complexity_score, risk_level, channel, **kwargs):
        recorded_calls.append({
            "task_type": task_type,
            "complexity_score": complexity_score,
            "risk_level": risk_level,
            "channel": channel,
        })
        return {"provider": "gemini", "model": "gemini-3.7-flash", "thinking_level": "low", "role": "CODING"}

    monkeypatch.setattr(harness.router, "select_engine", mock_select_engine)

    # 1. Avec mission_profile="CODING"
    await harness.execute_task(
        task_prompt="Refactor database schema",
        session_id="test-session-profile-1",
        mission_profile="CODING"
    )
    assert len(recorded_calls) == 1
    assert recorded_calls[0]["task_type"] == "coding"

    # 2. Sans mission_profile -> fallback "general"
    await harness.execute_task(
        task_prompt="Simple question",
        session_id="test-session-profile-2"
    )
    assert len(recorded_calls) == 2
    assert recorded_calls[1]["task_type"] == "general"
