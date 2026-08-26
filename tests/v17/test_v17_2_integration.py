import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from v17.api.router import router
from v17.state.service import product_state_service
from v17.events.buffer import global_event_buffer

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_v17_2_state_and_events_api():
    # Emit state event
    product_state_service.emit_snapshot_event()
    res = client.get("/api/v17/product/events/recent?limit=5")
    assert res.status_code == 200
    events = res.json()
    assert len(events) >= 1
    assert events[0]["event_type"] == "system.snapshot"
