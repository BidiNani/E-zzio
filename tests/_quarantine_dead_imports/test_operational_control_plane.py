import pytest
import re
from fastapi.testclient import TestClient
from interfaces.api.server import app

@pytest.fixture
def client():
    return TestClient(app)

def test_control_plane_readiness_diagnostics(client):
    res = client.get("/api/v1/health/readiness")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert data["status"] in ["READY", "DEGRADED", "NOT_READY"]
    
    checks = data["checks"]
    assert "process_alive" in checks
    assert "database_ready" in checks
    assert "memory_ready" in checks
    assert "model_ready" in checks
    assert "research_ready" in checks

def test_control_plane_system_metrics_and_zero_secret_leak(client):
    res = client.get("/api/v1/system/status")
    assert res.status_code == 200
    data = res.json()
    assert data["service"] == "E-ZZIO OS"
    assert data["status"] == "ONLINE"
    assert "memory" in data
    assert "cpu_percent" in data
    
    # Audit de sécurité : aucune clé ou token ne doit être exposé
    raw_text = res.text
    assert not re.search(r"AIzaSy[A-Za-z0-9_-]{33}", raw_text)
    assert not re.search(r"tvly-[A-Za-z0-9]{32}", raw_text)
    assert not re.search(r"jina_[A-Za-z0-9]{32}", raw_text)
