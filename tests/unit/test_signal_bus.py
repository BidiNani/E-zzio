"""Tests pour core/signals/signal_bus.py.

Bus d'événements asynchrone découplé. 100% testable :
- asyncio stdlib
- pytest-asyncio en mode strict (chaque test async doit être décoré)

Fonctions :
- SignalEvent (dataclass)
- SignalBus.connect / disconnect
- SignalBus.emit / emit_async
- SignalBus.get_event_history
- singleton signal_bus
"""
from __future__ import annotations

import asyncio

import pytest

from core.signals.signal_bus import SignalBus, SignalEvent, signal_bus

# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def bus():
    """Bus isolé par test (pas le singleton)."""
    return SignalBus()


# ============================================================
# 1. SignalEvent
# ============================================================

class TestSignalEvent:
    def test_basic_creation(self):
        evt = SignalEvent(name="test")
        assert evt.name == "test"
        assert evt.payload == {}

    def test_payload_custom(self):
        evt = SignalEvent(name="test", payload={"key": "value"})
        assert evt.payload == {"key": "value"}

    def test_timestamp_field_exists(self):
        evt = SignalEvent(name="test")
        assert isinstance(evt.timestamp, (int, float))

    def test_payload_default_factory_isolation(self):
        """Deux events ne partagent pas le même dict."""
        e1 = SignalEvent(name="a")
        e2 = SignalEvent(name="b")
        e1.payload["x"] = 1
        assert "x" not in e2.payload


# ============================================================
# 2. Singleton
# ============================================================

class TestSingleton:
    def test_singleton_exists(self):
        assert signal_bus is not None
        assert isinstance(signal_bus, SignalBus)

    def test_singleton_has_history(self):
        assert hasattr(signal_bus, "_history")


# ============================================================
# 3. connect
# ============================================================

class TestConnect:
    def test_connect_sync(self, bus):
        def cb(payload):
            pass
        bus.connect("test", cb)
        assert cb in bus._listeners["test"]

    def test_connect_async(self, bus):
        async def cb(payload):
            pass
        bus.connect("test", cb)
        assert cb in bus._async_listeners["test"]

    def test_connect_duplicate_ignored(self, bus):
        """Connecter deux fois le même callback → une seule entrée."""
        def cb(payload):
            pass
        bus.connect("test", cb)
        bus.connect("test", cb)
        assert len(bus._listeners["test"]) == 1

    def test_connect_multiple_callbacks(self, bus):
        def cb1(payload):
            pass
        def cb2(payload):
            pass
        bus.connect("test", cb1)
        bus.connect("test", cb2)
        assert len(bus._listeners["test"]) == 2

    def test_connect_different_signals(self, bus):
        def cb(payload):
            pass
        bus.connect("sig1", cb)
        bus.connect("sig2", cb)
        assert "sig1" in bus._listeners
        assert "sig2" in bus._listeners


# ============================================================
# 4. disconnect
# ============================================================

class TestDisconnect:
    def test_disconnect_sync(self, bus):
        def cb(payload):
            pass
        bus.connect("test", cb)
        bus.disconnect("test", cb)
        assert cb not in bus._listeners["test"]

    def test_disconnect_async(self, bus):
        async def cb(payload):
            pass
        bus.connect("test", cb)
        bus.disconnect("test", cb)
        assert cb not in bus._async_listeners["test"]

    def test_disconnect_unknown_signal(self, bus):
        """Disconnect sur signal inconnu → pas d'exception."""
        def cb(payload):
            pass
        bus.disconnect("nonexistent", cb)  # Ne doit pas lever

    def test_disconnect_unknown_callback(self, bus):
        """Disconnect d'un callback non connecté → pas d'exception."""
        def cb1(payload):
            pass
        def cb2(payload):
            pass
        bus.connect("test", cb1)
        bus.disconnect("test", cb2)  # Ne doit pas lever
        assert cb1 in bus._listeners["test"]


# ============================================================
# 5. emit (synchrone)
# ============================================================

class TestEmit:
    def test_emit_calls_sync_listener(self, bus):
        received = []
        def cb(payload):
            received.append(payload)
        bus.connect("test", cb)
        bus.emit("test", {"x": 1})
        assert received == [{"x": 1}]

    def test_emit_empty_payload(self, bus):
        received = []
        def cb(payload):
            received.append(payload)
        bus.connect("test", cb)
        bus.emit("test")
        assert received == [{}]

    def test_emit_none_payload_becomes_empty_dict(self, bus):
        received = []
        def cb(payload):
            received.append(payload)
        bus.connect("test", cb)
        bus.emit("test", None)
        assert received == [{}]

    def test_emit_no_listener_no_error(self, bus):
        """Émettre sur signal sans listener → pas d'exception."""
        bus.emit("test", {"x": 1})

    def test_emit_listener_exception_caught(self, bus):
        """Un listener qui lève ne casse pas les suivants."""
        received = []
        def cb_bad(payload):
            raise RuntimeError("boom")
        def cb_good(payload):
            received.append(payload)
        bus.connect("test", cb_bad)
        bus.connect("test", cb_good)
        bus.emit("test", {"x": 1})  # Ne doit pas lever
        assert received == [{"x": 1}]

    def test_emit_multiple_listeners(self, bus):
        received = []
        def cb1(payload):
            received.append("cb1")
        def cb2(payload):
            received.append("cb2")
        bus.connect("test", cb1)
        bus.connect("test", cb2)
        bus.emit("test")
        assert "cb1" in received
        assert "cb2" in received


# ============================================================
# 6. emit_async
# ============================================================

class TestEmitAsync:
    @pytest.mark.asyncio
    async def test_emit_async_calls_sync_listener(self, bus):
        received = []
        def cb(payload):
            received.append(payload)
        bus.connect("test", cb)
        await bus.emit_async("test", {"x": 1})
        assert received == [{"x": 1}]

    @pytest.mark.asyncio
    async def test_emit_async_calls_async_listener(self, bus):
        received = []
        async def cb(payload):
            received.append(payload)
        bus.connect("test", cb)
        await bus.emit_async("test", {"x": 1})
        assert received == [{"x": 1}]

    @pytest.mark.asyncio
    async def test_emit_async_sync_then_async_order(self, bus):
        """Les sync sont appelés avant les async."""
        order = []
        def sync_cb(payload):
            order.append("sync")
        async def async_cb(payload):
            order.append("async")
        bus.connect("test", sync_cb)
        bus.connect("test", async_cb)
        await bus.emit_async("test")
        assert order == ["sync", "async"]

    @pytest.mark.asyncio
    async def test_emit_async_sync_error_caught(self, bus):
        received = []
        def cb_bad(payload):
            raise RuntimeError("boom")
        def cb_good(payload):
            received.append("ok")
        bus.connect("test", cb_bad)
        bus.connect("test", cb_good)
        await bus.emit_async("test")
        assert "ok" in received

    @pytest.mark.asyncio
    async def test_emit_async_async_error_caught(self, bus):
        received = []
        async def cb_bad(payload):
            raise RuntimeError("boom")
        async def cb_good(payload):
            received.append("ok")
        bus.connect("test", cb_bad)
        bus.connect("test", cb_good)
        await bus.emit_async("test")
        assert "ok" in received

    @pytest.mark.asyncio
    async def test_emit_async_no_listener(self, bus):
        await bus.emit_async("test")  # Ne doit pas lever


# ============================================================
# 7. Historique
# ============================================================

class TestHistory:
    @pytest.mark.asyncio
    async def test_emit_async_appends_to_history(self, bus):
        await bus.emit_async("test", {"x": 1})
        history = bus.get_event_history()
        assert len(history) == 1
        assert history[0]["name"] == "test"
        assert history[0]["payload"] == {"x": 1}

    @pytest.mark.asyncio
    async def test_history_filter_by_name(self, bus):
        await bus.emit_async("sig1", {"a": 1})
        await bus.emit_async("sig2", {"b": 2})
        await bus.emit_async("sig1", {"c": 3})
        history = bus.get_event_history("sig1")
        assert len(history) == 2
        for item in history:
            assert item["name"] == "sig1"

    @pytest.mark.asyncio
    async def test_history_all(self, bus):
        await bus.emit_async("sig1")
        await bus.emit_async("sig2")
        history = bus.get_event_history()
        assert len(history) == 2

    def test_history_empty(self, bus):
        assert bus.get_event_history() == []

    @pytest.mark.asyncio
    async def test_history_max_limit(self, bus):
        """L'historique est limité à 100 entrées."""
        for i in range(150):
            await bus.emit_async("test", {"i": i})
        history = bus.get_event_history()
        assert len(history) == 100
        # La première entrée doit être i=50 (les 50 premières ont été pop)
        assert history[0]["payload"]["i"] == 50


# ============================================================
# 8. Cas intégrés
# ============================================================

class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_cycle(self, bus):
        """Connect → emit_async → disconnect → emit_async."""
        received = []
        def cb(payload):
            received.append(payload)

        bus.connect("cycle", cb)
        await bus.emit_async("cycle", {"step": 1})

        bus.disconnect("cycle", cb)
        await bus.emit_async("cycle", {"step": 2})

        # Seule la première émission a été reçue
        assert received == [{"step": 1}]

    def test_two_buses_isolated(self):
        """Deux bus séparés n'interfèrent pas."""
        bus1 = SignalBus()
        bus2 = SignalBus()

        received1 = []
        received2 = []
        def cb1(payload):
            received1.append(payload)
        def cb2(payload):
            received2.append(payload)

        bus1.connect("test", cb1)
        bus2.connect("test", cb2)

        bus1.emit("test", {"from": "bus1"})

        assert received1 == [{"from": "bus1"}]
        assert received2 == []
