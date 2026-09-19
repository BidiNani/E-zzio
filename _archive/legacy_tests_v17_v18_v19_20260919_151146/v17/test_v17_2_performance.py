import pytest
import time
from fastapi import FastAPI
from fastapi.testclient import TestClient
from v17.api.router import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_v17_2_state_latency():
    t0 = time.perf_counter()
    res = client.get("/api/v17/product/state")
    t1 = time.perf_counter()
    assert res.status_code == 200
    lat_ms = (t1 - t0) * 1000
    assert lat_ms < 50 # Performance target < 50ms
