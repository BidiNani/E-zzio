import pytest
import time
from fastapi import FastAPI
from fastapi.testclient import TestClient
from v17.api.router import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_v17_3_ui_performance():
    t0 = time.perf_counter()
    res = client.get("/api/v17/product/ui")
    t1 = time.perf_counter()
    assert res.status_code == 200
    # UI load under 50ms
    assert (t1 - t0) < 0.05
