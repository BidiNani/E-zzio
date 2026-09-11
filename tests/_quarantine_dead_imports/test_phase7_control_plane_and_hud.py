import pytest
import re
from fastapi.testclient import TestClient
from interfaces.api.server import app

@pytest.fixture
def client():
    return TestClient(app)

def test_phase7_control_plane_endpoints_consistency(client):
    # 1. Readiness
    r1 = client.get("/api/v1/health/readiness")
    assert r1.status_code == 200
    assert r1.json()["status"] in ["READY", "DEGRADED", "NOT_READY"]
    
    # 2. System status
    r2 = client.get("/api/v1/system/status")
    assert r2.status_code == 200
    assert r2.json()["service"] == "E-ZZIO OS"
    
    # 3. Tasks list
    r3 = client.post("/api/v1/tasks/", json={"objective": "Test HUD Task", "session_id": "SESS_HUD"})
    assert r3.status_code == 200
    t_id = r3.json()["task_id"]
    
    r4 = client.get(f"/api/v1/tasks/{t_id}")
    assert r4.status_code == 200
    assert r4.json()["status"] == "CREATED"

def test_phase7_web_hud_experience(client):
    # Accès à la racine et au HUD
    res = client.get("/")
    assert res.status_code == 200
    assert "E‑ZZIO" in res.text
    assert "Dashboard" in res.text
