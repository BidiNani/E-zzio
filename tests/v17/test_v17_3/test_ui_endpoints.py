import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from v17.api.router import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_v17_3_ui_served_successfully():
    res = client.get("/api/v17/product/ui")
    assert res.status_code == 200
    assert "E-ZZIO V17.3 — Command Center" in res.text
    assert "GUARDIAN LOCKED" in res.text
    assert "Cockpit Overview" in res.text
