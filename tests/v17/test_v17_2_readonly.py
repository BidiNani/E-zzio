import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from v17.api.router import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_v17_2_readonly_no_mutation():
    res_state = client.get("/api/v17/product/state")
    assert res_state.status_code == 200
    res_events = client.get("/api/v17/product/events")
    assert res_events.status_code == 200
