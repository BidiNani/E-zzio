"""tests/test_event_bus.py - Validation stricte du bus d'événements et de la persistance WAL."""

import asyncio
from pathlib import Path

import pytest

from core.bus import AgentEvent, EventBus


@pytest.fixture
def temp_bus(tmp_path: Path) -> EventBus:
    db_file = tmp_path / "test_ezzio.db"
    return EventBus(db_path=db_file)


@pytest.mark.asyncio
async def test_register_run_and_emit_event(temp_bus: EventBus) -> None:
    run_id = "run_test_001"
    temp_bus.register_run(run_id, prompt="Corriger l'addon Lua", profile="autonome")

    event = AgentEvent(
        run_id=run_id,
        event_type="plan",
        agent_id="Orchestrateur",
        payload={"steps": ["Lire le code", "Appliquer le diff", "Lancer les tests"]},
        requires_approval=False,
    )

    emitted = await temp_bus.emit(event)
    assert emitted.event_id is not None
    assert emitted.event_id > 0

    events = temp_bus.get_run_events(run_id)
    assert len(events) == 1
    assert events[0]["event_type"] == "plan"
    assert events[0]["payload"]["steps"][0] == "Lire le code"
    assert events[0]["requires_approval"] is False


@pytest.mark.asyncio
async def test_event_bus_pub_sub(temp_bus: EventBus) -> None:
    run_id = "run_test_002"
    temp_bus.register_run(run_id, prompt="Test diffusion")

    queue = temp_bus.subscribe(run_id)

    event = AgentEvent(
        run_id=run_id,
        event_type="tool_call",
        agent_id="Agent Terminal",
        payload={"command": "pytest -q"},
        requires_approval=True,
    )

    await temp_bus.emit(event)

    received = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert received.run_id == run_id
    assert received.event_type == "tool_call"
    assert received.requires_approval is True

    temp_bus.unsubscribe(run_id, queue)
    assert run_id not in temp_bus._subscribers
