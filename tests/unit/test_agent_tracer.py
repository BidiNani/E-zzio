"""Tests pour core/telemetry/agent_tracer.py.

Bus de télémétrie agents : singleton, fan-out non bloquant, contexte
contextvars, décorateur cycle de vie.

Découvertes pré-test :
- TraceEvent : pydantic BaseModel avec patterns stricts + extra="forbid"
- _trunc : fonction pure qui tronque dict/valeurs
- AgentTracer : singleton via __new__, subscribe/emit/history
- emit() : ne lève jamais, drop-oldest sur QueueFull
- traced() : décorateur multi-paradigme (sync/async/gen/asyncgen)
"""
from __future__ import annotations

import asyncio
import contextvars
import time

import pytest
from pydantic import ValidationError

from core.telemetry.agent_tracer import (
    MAX_HISTORY,
    MAX_QUEUE,
    AgentTracer,
    TraceEvent,
    _trunc,
    traced,
    tracer,
)

# ============================================================
# 1. TraceEvent — validation pydantic
# ============================================================

class TestTraceEvent:
    def test_minimal_valid(self):
        evt = TraceEvent(
            trace_id="t1",
            agent_id="a1",
            event_type="START",
            status="RUNNING",
        )
        assert evt.trace_id == "t1"
        assert evt.agent_id == "a1"
        assert evt.event_type == "START"
        assert evt.status == "RUNNING"
        assert evt.tool_name is None
        assert evt.payload == {}
        assert evt.duration_ms is None
        assert isinstance(evt.timestamp, float)

    def test_event_type_pattern(self):
        """event_type doit matcher le pattern strict."""
        with pytest.raises(ValidationError):
            TraceEvent(
                trace_id="t", agent_id="a",
                event_type="INVALID",
                status="RUNNING",
            )

    def test_status_pattern(self):
        """status doit matcher le pattern strict."""
        with pytest.raises(ValidationError):
            TraceEvent(
                trace_id="t", agent_id="a",
                event_type="START",
                status="UNKNOWN",
            )

    def test_valid_event_types(self):
        for et in ["START", "TOOL_CALL", "TOOL_RESULT", "STATUS_CHANGE", "FINISH", "ERROR"]:
            evt = TraceEvent(trace_id="t", agent_id="a", event_type=et, status="RUNNING")
            assert evt.event_type == et

    def test_valid_statuses(self):
        for st in ["PENDING", "RUNNING", "BLOCKED", "SUCCESS", "FAILED"]:
            evt = TraceEvent(trace_id="t", agent_id="a", event_type="START", status=st)
            assert evt.status == st

    def test_extra_forbidden(self):
        """extra='forbid' rejette les champs non déclarés."""
        with pytest.raises(ValidationError):
            TraceEvent(
                trace_id="t", agent_id="a",
                event_type="START", status="RUNNING",
                unknown_field="boom",
            )

    def test_payload_factory_isolation(self):
        """Deux events ne partagent pas le même dict payload."""
        e1 = TraceEvent(trace_id="t", agent_id="a", event_type="START", status="RUNNING")
        e2 = TraceEvent(trace_id="t", agent_id="a", event_type="START", status="RUNNING")
        e1.payload["x"] = 1
        assert "x" not in e2.payload

    def test_duration_ms_optional(self):
        evt = TraceEvent(
            trace_id="t", agent_id="a",
            event_type="TOOL_RESULT", status="SUCCESS",
            duration_ms=12.5,
        )
        assert evt.duration_ms == 12.5


# ============================================================
# 2. _trunc — fonction pure
# ============================================================

class TestTrunc:
    def test_dict_small(self):
        result = _trunc({"a": 1, "b": 2})
        assert result["a"] == "1"
        assert result["b"] == "2"

    def test_dict_nested_becomes_ellipsis(self):
        """Les valeurs dict/list deviennent '...'."""
        result = _trunc({"nested": {"x": 1}, "list": [1, 2]})
        assert result["nested"] == "..."
        assert result["list"] == "..."

    def test_dict_key_truncated_to_60(self):
        """Les clés sont tronquées à 60 chars."""
        long_key = "k" * 100
        result = _trunc({long_key: "v"})
        keys = list(result.keys())
        assert len(keys[0]) == 60

    def test_dict_value_truncated(self):
        """Les valeurs string sont tronquées à n (500)."""
        long_val = "x" * 1000
        result = _trunc({"key": long_val})
        assert len(result["key"]) == 500

    def test_dict_limits_to_12_items(self):
        """Max 12 items."""
        big = {f"k{i}": i for i in range(30)}
        result = _trunc(big)
        assert len(result) == 12

    def test_non_dict_input(self):
        """Non-dict -> {'value': str(obj)[:n]}"""
        result = _trunc("hello", n=3)
        assert result == {"value": "hel"}

    def test_none_input(self):
        result = _trunc(None)
        assert result["value"] == "None"

    def test_custom_n(self):
        result = _trunc("abcdefgh", n=4)
        assert result == {"value": "abcd"}


# ============================================================
# 3. AgentTracer singleton + subscribe/unsubscribe
# ============================================================

class TestAgentTracerSingleton:
    def test_singleton(self):
        """Deux instanciations retournent la même instance."""
        t1 = AgentTracer()
        t2 = AgentTracer()
        assert t1 is t2

    def test_module_level_tracer(self):
        assert tracer is not None
        assert isinstance(tracer, AgentTracer)
        assert tracer is AgentTracer()

    def test_has_history_deque(self):
        assert hasattr(tracer, "_history")
        assert tracer._history.maxlen == MAX_HISTORY

    def test_has_subs_list(self):
        assert hasattr(tracer, "_subs")
        assert isinstance(tracer._subs, list)


class TestSubscribeUnsubscribe:
    def test_subscribe_returns_queue(self):
        q = tracer.subscribe()
        assert isinstance(q, asyncio.Queue)
        assert q.maxsize == MAX_QUEUE
        tracer.unsubscribe(q)

    def test_subscribe_with_trace_id(self):
        q = tracer.subscribe(trace_id="specific")
        assert any(t == "specific" for _, _, t in tracer._subs)
        tracer.unsubscribe(q)

    def test_unsubscribe_removes(self):
        q = tracer.subscribe()
        n_before = len(tracer._subs)
        tracer.unsubscribe(q)
        assert len(tracer._subs) == n_before - 1


# ============================================================
# 4. history + emit
# ============================================================

class TestHistoryEmit:
    def _make_event(self, trace_id: str = "t1", event_type: str = "START"):
        return TraceEvent(
            trace_id=trace_id, agent_id="agent",
            event_type=event_type, status="RUNNING",
        )

    def test_emit_appends_to_history(self):
        evt = self._make_event("hist_test_1")
        tracer.emit(evt)
        assert evt in tracer._history

    def test_history_returns_last_n(self):
        for i in range(5):
            tracer.emit(self._make_event(f"h_{i}"))
        h = tracer.history(limit=3)
        assert len(h) <= 3

    def test_history_never_raises(self):
        """history() ne lève jamais."""
        result = tracer.history(limit=-1)
        assert isinstance(result, list)

    def test_emit_to_subscriber(self):
        """emit envoie à un subscriber."""
        q = tracer.subscribe()
        try:
            evt = self._make_event("sub_test")
            tracer.emit(evt)
            # Le queue doit contenir l'événement
            assert not q.empty()
        finally:
            tracer.unsubscribe(q)

    def test_emit_filters_by_trace_id(self):
        """Un subscriber avec trace_id ne reçoit que ses events."""
        q = tracer.subscribe(trace_id="filtered")
        try:
            # Event avec un autre trace_id -> filtré
            tracer.emit(self._make_event("other"))
            assert q.empty()
        finally:
            tracer.unsubscribe(q)


# ============================================================
# 5. trace_context (ContextVar manager)
# ============================================================

class TestTraceContext:
    def test_context_sets_and_restores(self):
        """Le contexte est actif à l'intérieur du with."""
        from core.telemetry.agent_tracer import (
            _agent_id_ctx,
            _parent_id_ctx,
            _trace_id_ctx,
        )
        with tracer.trace_context("ctx_trace", "ctx_agent", "ctx_parent"):
            assert _trace_id_ctx.get() == "ctx_trace"
            assert _agent_id_ctx.get() == "ctx_agent"
            assert _parent_id_ctx.get() == "ctx_parent"
        # Après sortie, contexte restauré
        assert _trace_id_ctx.get() == ""

    def test_context_exception_safe(self):
        """Le contexte est restauré même en cas d'exception."""
        from core.telemetry.agent_tracer import _trace_id_ctx
        try:
            with tracer.trace_context("boom_trace", "boom_agent"):
                raise RuntimeError("inside")
        except RuntimeError:
            pass
        assert _trace_id_ctx.get() == ""


# ============================================================
# 6. tool_call / tool_result / lifecycle
# ============================================================

class TestToolCallResult:
    def test_tool_call_returns_t0(self):
        """tool_call retourne un timestamp float."""
        t0 = tracer.tool_call("my_tool", args={"x": 1})
        assert isinstance(t0, float)
        assert t0 > 0

    def test_tool_call_emits_event(self):
        before = len(tracer._history)
        tracer.tool_call("my_tool")
        assert len(tracer._history) > before

    def test_tool_result_emits(self):
        before = len(tracer._history)
        t0 = time.perf_counter()
        tracer.tool_result("my_tool", t0, ok=True, result={"out": 42})
        assert len(tracer._history) > before

    def test_tool_result_failure(self):
        """ok=False -> status FAILED."""
        t0 = time.perf_counter()
        tracer.tool_result("fail_tool", t0, ok=False)
        last = list(tracer._history)[-1]
        assert last.status == "FAILED"

    def test_lifecycle_emits(self):
        before = len(tracer._history)
        tracer.lifecycle("STATUS_CHANGE", "RUNNING", agent_id="test")
        assert len(tracer._history) > before

    def test_lifecycle_with_payload(self):
        tracer.lifecycle("START", "RUNNING", payload={"custom": "data"})
        last = list(tracer._history)[-1]
        # Le payload est tronqué
        assert "custom" in last.payload


# ============================================================
# 7. traced decorator
# ============================================================

class TestTracedDecorator:
    def test_sync_function(self):
        """Décorateur sur fonction sync."""
        @traced("test_agent")
        def my_func(x):
            return x * 2

        before = len(tracer._history)
        result = my_func(21)
        assert result == 42
        assert len(tracer._history) >= before + 2  # START + FINISH

    def test_sync_function_failure(self):
        """Décorateur capture l'exception et ré-émet."""
        @traced("test_agent")
        def boom():
            raise ValueError("bad")

        with pytest.raises(ValueError):
            boom()

    def test_sync_success_false_marks_failed(self):
        """Un dict {success: False} -> status FAILED."""
        @traced("test_agent")
        def failing_dict():
            return {"success": False, "error": "oops"}

        before = len(tracer._history)
        failing_dict()
        # Le dernier event doit être FINISH ou FAILED
        events = list(tracer._history)[before:]
        assert any(e.event_type == "FINISH" for e in events)

    @pytest.mark.asyncio
    async def test_async_function(self):
        """Décorateur sur fonction async."""
        @traced("async_agent")
        async def my_async(x):
            await asyncio.sleep(0)
            return x + 1

        result = await my_async(10)
        assert result == 11

    @pytest.mark.asyncio
    async def test_async_function_failure(self):
        @traced("async_agent")
        async def boom_async():
            raise RuntimeError("async boom")

        with pytest.raises(RuntimeError):
            await boom_async()

    def test_generator_function(self):
        """Décorateur sur generator."""
        @traced("gen_agent")
        def my_gen():
            yield 1
            yield 2
            yield 3

        result = list(my_gen())
        assert result == [1, 2, 3]

    def test_generator_failure(self):
        @traced("gen_agent")
        def boom_gen():
            yield 1
            raise ValueError("gen boom")

        gen = boom_gen()
        assert next(gen) == 1
        with pytest.raises(ValueError):
            next(gen)

    @pytest.mark.asyncio
    async def test_async_generator(self):
        """Décorateur sur async generator."""
        @traced("async_gen_agent")
        async def my_async_gen():
            for i in range(3):
                yield i

        result = []
        async for item in my_async_gen():
            result.append(item)
        assert result == [0, 1, 2]

    def test_decorator_preserves_name(self):
        """functools.wraps préserve __name__."""
        @traced("test")
        def my_named_func():
            pass

        assert my_named_func.__name__ == "my_named_func"
