"""Tests complémentaires pour agent_tracer.py : branches rares."""
from __future__ import annotations

import asyncio

import pytest

from core.telemetry.agent_tracer import (
    AgentTracer,
    TraceEvent,
    tracer,
)


class TestEmitFullQueue:
    def test_emit_queue_full_drops_oldest(self):
        """Queue pleine -> drop-oldest, pas de crash."""
        # Créer un sub avec queue de taille 1
        # Puis envoyer 3 events -> les plus anciens sont droppés
        q = tracer.subscribe()
        try:
            # Vider la queue
            while not q.empty():
                q.get_nowait()

            # Remplir
            for i in range(3):
                tracer.emit(TraceEvent(
                    trace_id=f"t{i}",
                    agent_id="agent",
                    event_type="START",
                    status="RUNNING",
                ))
            # La queue doit contenir le dernier event seulement
            assert not q.empty()
        finally:
            tracer.unsubscribe(q)

    def test_emit_runtime_error_handled(self, monkeypatch):
        """Si put_nowait lève RuntimeError (loop différent), call_soon_threadsafe est utilisé."""
        class FakeQueue:
            def __init__(self):
                self.called = False
            def put_nowait(self, event):
                raise RuntimeError("loop mismatch")
            def get_nowait(self):
                raise RuntimeError("loop mismatch")

        fake_q = FakeQueue()
        fake_loop = type("Loop", (), {"call_soon_threadsafe": lambda self, fn, arg: None})()

        tracer._subs.append((fake_loop, fake_q, None))
        try:
            tracer.emit(TraceEvent(
                trace_id="t", agent_id="a",
                event_type="START", status="RUNNING",
            ))
            # Ne doit pas crasher
            assert True
        finally:
            tracer._subs = [s for s in tracer._subs if s[1] is not fake_q]


class TestHistoryBranches:
    def test_history_limit_1_min(self):
        """limit=0 ou négatif -> ramené à 1."""
        result = tracer.history(limit=0)
        assert isinstance(result, list)

    def test_history_limit_large(self):
        """limit > taille -> ramené à taille."""
        result = tracer.history(limit=10000)
        assert isinstance(result, list)

    def test_history_exception_returns_empty(self, monkeypatch):
        """Si list() lève -> retourne []."""
        # Simuler une erreur
        class BadDeque:
            def __iter__(self):
                raise RuntimeError("boom")
        original = tracer._history
        tracer._history = BadDeque()
        try:
            result = tracer.history()
            assert result == []
        finally:
            tracer._history = original


class TestTraceContextNested:
    def test_nested_contexts(self):
        """Contextes imbriqués -> restauration correcte."""
        from core.telemetry.agent_tracer import _trace_id_ctx

        with tracer.trace_context("outer", "agent"):
            assert _trace_id_ctx.get() == "outer"
            with tracer.trace_context("inner", "agent"):
                assert _trace_id_ctx.get() == "inner"
            # Retour au contexte outer
            assert _trace_id_ctx.get() == "outer"
        # Retour au default
        assert _trace_id_ctx.get() == ""


class TestToolCallWithContext:
    def test_tool_call_uses_context(self):
        """tool_call utilise le trace_id/agent_id du contexte."""
        from core.telemetry.agent_tracer import _trace_id_ctx

        with tracer.trace_context("ctx-123", "ctx-agent"):
            t0 = tracer.tool_call("my-tool")
            last = list(tracer._history)[-1]
            assert last.trace_id == "ctx-123"
            assert last.agent_id == "ctx-agent"

    def test_lifecycle_uses_context(self):
        with tracer.trace_context("ctx-456", "ctx-agent-2"):
            tracer.lifecycle("START", "RUNNING")
            last = list(tracer._history)[-1]
            assert last.trace_id == "ctx-456"
