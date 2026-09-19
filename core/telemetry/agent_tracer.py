"""E-ZZIO — bus de télémétrie agents (singleton, fan-out non bloquant)."""
from __future__ import annotations

import asyncio
import contextvars
import logging
import time

from pydantic import BaseModel, Field

MAX_QUEUE = 1000
MAX_HISTORY = 1000

logger = logging.getLogger("ezzio.telemetry")

_trace_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")
_agent_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("agent_id", default="")
_parent_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("parent_id", default=None)


class TraceEvent(BaseModel):
    trace_id: str
    timestamp: float = Field(default_factory=time.time)
    agent_id: str
    parent_id: str | None = None
    event_type: str = Field(pattern="^(START|TOOL_CALL|TOOL_RESULT|STATUS_CHANGE|FINISH|ERROR)$")
    status: str = Field(pattern="^(PENDING|RUNNING|BLOCKED|SUCCESS|FAILED)$")
    tool_name: str | None = None
    payload: dict = Field(default_factory=dict)
    duration_ms: float | None = None

    model_config = {"extra": "forbid"}


def _trunc(obj, n: int = 500) -> dict:
    if isinstance(obj, dict):
        return {str(k)[:60]: (str(v)[:n] if not isinstance(v, (dict, list)) else "...") for k, v in list(obj.items())[:12]}
    return {"value": str(obj)[:n]}


class AgentTracer:
    """Singleton : emit() synchrone, jamais bloquant, jamais levant."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subs: list[tuple[asyncio.AbstractEventLoop, asyncio.Queue, str | None]] = []
            from collections import deque as _deque
            cls._instance._history = _deque(maxlen=MAX_HISTORY)
        return cls._instance

    def subscribe(self, trace_id: str | None = None) -> asyncio.Queue:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
        q: asyncio.Queue = asyncio.Queue(maxsize=MAX_QUEUE)
        self._subs.append((loop, q, trace_id))
        return q

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subs = [(entry, q, t) for entry, q, t in self._subs if q is not queue]

    def history(self, limit: int = 100) -> list:
        """Derniers événements (buffer borné MAX_HISTORY)."""
        try:
            return list(self._history)[-max(1, limit):]
        except Exception:
            return []

    def emit(self, event: TraceEvent) -> None:
        try:
            self._history.append(event)
        except Exception:
            pass
        for loop, q, filt in list(self._subs):
            if filt is not None and filt != event.trace_id:
                continue
            try:
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    try:
                        q.get_nowait()  # drop-oldest, jamais de croissance infinie
                    except Exception:
                        pass
                    try:
                        q.put_nowait(event)
                    except Exception:
                        pass
            except RuntimeError:
                # File liée à une autre boucle : livraison thread-safe.
                try:
                    loop.call_soon_threadsafe(q.put_nowait, event)
                except Exception:
                    pass
            except Exception:
                pass

    # --- API contextuelle ---
    def trace_context(self, trace_id: str, agent_id: str, parent_id: str | None = None):

        class _Ctx:
            def __enter__(_s):
                _s.toks = (_trace_id_ctx.set(trace_id),
                           _agent_id_ctx.set(agent_id),
                           _parent_id_ctx.set(parent_id))
                _s.vars = (_trace_id_ctx, _agent_id_ctx, _parent_id_ctx)
                return _s

            def __exit__(_s, *a):
                for var, tok in zip(_s.vars, _s.toks):
                    try:
                        var.reset(tok)
                    except Exception:
                        pass
                return False
        return _Ctx()

    def tool_call(self, tool_name: str, args=None, agent_id: str = "",
                  trace_id: str = "", parent_id: str | None = None) -> float:
        t0 = time.perf_counter()
        try:
            self.emit(TraceEvent(
                trace_id=trace_id or _trace_id_ctx.get() or "adhoc",
                agent_id=agent_id or _agent_id_ctx.get() or "unknown",
                parent_id=parent_id if parent_id is not None else _parent_id_ctx.get(),
                event_type="TOOL_CALL", status="RUNNING",
                tool_name=tool_name, payload=_trunc(args or {})))
        except Exception:
            pass
        return t0

    def tool_result(self, tool_name: str, t0: float, ok: bool = True,
                    result=None, agent_id: str = "", trace_id: str = "") -> None:
        try:
            self.emit(TraceEvent(
                trace_id=trace_id or _trace_id_ctx.get() or "adhoc",
                agent_id=agent_id or _agent_id_ctx.get() or "unknown",
                parent_id=_parent_id_ctx.get(),
                event_type="TOOL_RESULT",
                status="SUCCESS" if ok else "FAILED",
                tool_name=tool_name,
                payload=_trunc({"output": result}),
                duration_ms=round((time.perf_counter() - t0) * 1000, 2)))
        except Exception:
            pass

    def lifecycle(self, event_type: str, status: str, agent_id: str = "",
                  trace_id: str = "", parent_id: str | None = None,
                  payload=None) -> None:
        try:
            self.emit(TraceEvent(
                trace_id=trace_id or _trace_id_ctx.get() or "adhoc",
                agent_id=agent_id or _agent_id_ctx.get() or "unknown",
                parent_id=parent_id if parent_id is not None else _parent_id_ctx.get(),
                event_type=event_type, status=status,
                payload=_trunc(payload or {})))
        except Exception:
            pass


tracer = AgentTracer()


def traced(agent_id: str):
    """Décorateur cycle de vie START/FINISH/ERROR (sync/async/gen/asyncgen)."""
    import functools
    import inspect as _inspect

    def deco(fn):
        @functools.wraps(fn)
        def _emit(et, st, payload=None):
            try:
                tracer.lifecycle(et, st, agent_id=agent_id, payload=payload or {})
            except Exception:
                pass

        if _inspect.isasyncgenfunction(fn):
            @functools.wraps(fn)
            async def _awrap(*a, **k):
                _emit("START", "RUNNING")
                try:
                    async for item in fn(*a, **k):
                        yield item
                except Exception as exc:
                    _emit("ERROR", "FAILED", {"error": str(exc)[:500]})
                    raise
                _emit("FINISH", "SUCCESS")
            return _awrap
        if _inspect.isgeneratorfunction(fn):
            @functools.wraps(fn)
            def _wrap(*a, **k):
                _emit("START", "RUNNING")
                try:
                    for item in fn(*a, **k):
                        yield item
                except Exception as exc:
                    _emit("ERROR", "FAILED", {"error": str(exc)[:500]})
                    raise
                _emit("FINISH", "SUCCESS")
            return _wrap
        if _inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def _cwrap(*a, **k):
                _emit("START", "RUNNING")
                try:
                    out = await fn(*a, **k)
                except Exception as exc:
                    _emit("ERROR", "FAILED", {"error": str(exc)[:500]})
                    raise
                _emit("FINISH", "SUCCESS")
                return out
            return _cwrap

        @functools.wraps(fn)
        def _swrap(*a, **k):
            _emit("START", "RUNNING")
            try:
                out = fn(*a, **k)
            except Exception as exc:
                _emit("ERROR", "FAILED", {"error": str(exc)[:500]})
                raise
            ok = not (isinstance(out, dict) and out.get("success") is False)
            _emit("FINISH", "SUCCESS" if ok else "FAILED")
            return out
        return _swrap
    return deco
