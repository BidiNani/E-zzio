import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from interfaces.api.server import app

@pytest.fixture
def client():
    return TestClient(app)

def test_api_operational_health_readiness_e2e(client):
    res = client.get("/api/v1/health/readiness")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["READY", "DEGRADED", "NOT_READY"]
    assert "checks" in data

def test_api_operational_chat_e2e(client):
    mock_think_res = {
        "response": "Réponse HTTP E2E certifiée.",
        "intent": "chat",
        "provider": "ollama",
        "mode": "local_chat"
    }
    
    with patch("routers.chat._core.think", new_callable=AsyncMock) as mock_think:
        mock_think.return_value = mock_think_res
        
        payload = {
            "message": "Hello via HTTP Client",
            "user_id": "test_http_user",
            "session_id": "SESS_HTTP_E2E"
        }
        res = client.post("/api/v1/chat/", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["response"] == "Réponse HTTP E2E certifiée."
        assert data["provider"] == "ollama"
        assert data["session_id"] == "SESS_HTTP_E2E"
