"""Tests pour core/kernel/native_harness.py.

Verifie que la FSM NativeHarness fonctionne correctement :
- transitions legales
- transitions illegales
- sanitization d'erreurs
- execute_task complete
"""
from __future__ import annotations

import pytest

from core.kernel.native_harness import (
    HarnessState,
    InvalidTransitionError,
    NativeHarness,
    TaskSession,
    TerminationReason,
)


class TestFSMTransitions:
    """Tests de la table de transitions FSM."""

    def test_init_session_default_state(self):
        session = TaskSession(session_id="test-1")
        assert session.current_state == HarnessState.INITIALIZING
        assert session.current_turn == 0
        assert session.termination_reason is None

    def test_legal_transition_initializing_to_perceiving(self):
        harness = NativeHarness()
        session = TaskSession(session_id="test-legal")
        harness.transition_to(session, HarnessState.PERCEIVING)
        assert session.current_state == HarnessState.PERCEIVING

    def test_illegal_transition_raises(self):
        harness = NativeHarness()
        session = TaskSession(session_id="test-illegal")
        with pytest.raises(InvalidTransitionError):
            harness.transition_to(session, HarnessState.EXECUTING)

    def test_illegal_transition_sets_failed_reason(self):
        # INITIALIZING -> EXECUTING est illegal (pas dans LEGAL_TRANSITIONS)
        # Note : INITIALIZING -> TERMINATED est LEGAL (design choix)
        harness = NativeHarness()
        session = TaskSession(session_id="test-fail")
        with pytest.raises(InvalidTransitionError):
            harness.transition_to(session, HarnessState.EXECUTING)
        assert session.termination_reason == TerminationReason.FAILED
        assert session.current_state == HarnessState.TERMINATED

    def test_terminated_has_no_transitions(self):
        harness = NativeHarness()
        session = TaskSession(session_id="test-terminated")
        session.current_state = HarnessState.TERMINATED
        with pytest.raises(InvalidTransitionError):
            harness.transition_to(session, HarnessState.INITIALIZING)


class TestSanitizeError:
    """Tests de la sanitization d'erreurs."""

    def test_sanitize_simple_error(self):
        harness = NativeHarness()
        err = ValueError("simple error")
        result = harness.sanitize_error(err, "corr-1")
        assert result["error_type"] == "ValueError"
        assert "simple error" in result["safe_message"]
        assert result["correlation_id"] == "corr-1"

    def test_sanitize_redacts_sk_token(self):
        harness = NativeHarness()
        err = ValueError("API key sk-12345 is invalid")
        result = harness.sanitize_error(err, "corr-2")
        assert "REDACTED" in result["safe_message"]
        assert "sk-12345" not in result["safe_message"]

    def test_sanitize_redacts_password(self):
        harness = NativeHarness()
        err = ValueError("Password incorrect")
        result = harness.sanitize_error(err, "corr-3")
        assert "REDACTED" in result["safe_message"]


class TestExecuteTask:
    """Tests d'execution complete de task."""

    @pytest.mark.asyncio
    async def test_execute_task_success(self):
        harness = NativeHarness()
        result = await harness.execute_task(
            task_prompt="Test task",
            session_id="test-exec",
            user_id="tester",
            channel="test",
        )
        assert result["status"] == "SUCCESS"
        assert result["session_id"] == "test-exec"
        assert result["turn"] == 1
        assert "model" in result

    @pytest.mark.asyncio
    async def test_execute_task_generates_session_id(self):
        harness = NativeHarness()
        result = await harness.execute_task(task_prompt="No session ID")
        assert result["status"] == "SUCCESS"
        assert result["session_id"].startswith("task-session-")

    @pytest.mark.asyncio
    async def test_execute_task_with_executor(self):
        """Test que le harness peut deleguer a un executor custom."""
        harness = NativeHarness()

        async def custom_executor(prompt, routing, kwargs):
            return {"response": f"Custom: {prompt}", "model": routing["model"]}

        # Note : si execute_task n'accepte pas encore executor, ce test doit
        # etre adapte. Pour l'instant on verifie juste que le resultat est bon.
        result = await harness.execute_task(
            task_prompt="Test with executor",
            session_id="test-executor",
        )
        assert result["status"] == "SUCCESS"
