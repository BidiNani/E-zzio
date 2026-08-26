import pytest
import os
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from interfaces.api.server import app

@pytest.fixture
def client():
    return TestClient(app)

def test_readiness_all_ok_state(client):
    resp = client.get("/api/v1/health/readiness")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "checks" in data
    assert data["checks"]["process_alive"] is True
    # Ne doit jamais exposer de clés API ou tokens
    assert "api_key" not in data
    assert "token" not in data
    assert "secret" not in data

def test_readiness_database_down_state(client):
    with patch("os.path.exists", return_value=False):
        resp = client.get("/api/v1/health/readiness")
        assert resp.status_code == 200
        data = resp.json()
        assert data["checks"]["database_ready"] is False
        assert data["status"] == "NOT_READY"

def test_readiness_model_down_degraded_state(client):
    with patch("httpx.AsyncClient.get", side_effect=Exception("Ollama offline")):
        resp = client.get("/api/v1/health/readiness")
        assert resp.status_code == 200
        data = resp.json()
        assert data["checks"]["model_ready"] is False
        assert data["status"] in ["DEGRADED", "NOT_READY"]
