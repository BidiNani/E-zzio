import pytest
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers.chat import router as chat_router

app = FastAPI()
app.include_router(chat_router)


@pytest.fixture
def client():
    return TestClient(app)


def test_chat_endpoint_structure(client):
    payload = {"message": "Bonjour E-ZZIO", "user_id": "test_user_01"}
    mock_result = {
        "response": "Bonjour ! Prêt à exécuter vos ordres.",
        "intent": "local_chat",
        "provider": "ollama",
        "mode": "local_chat",
        "session_id": "sess_test_user_01",
        "data": {},
    }
    with patch("routers.chat._core.think", new_callable=AsyncMock) as mock_think:
        mock_think.return_value = mock_result
        resp = client.post("/api/v1/chat", json=payload)

        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "local_chat"
        assert data["provider"] == "ollama"
        assert "Bonjour" in data["response"]


def test_api_health_readiness_endpoint():
    from interfaces.api.server import app as full_app
    client = TestClient(full_app)
    resp = client.get("/api/v1/health/readiness")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "checks" in data
    assert data["checks"]["process_alive"] is True
    assert "database_ready" in data["checks"]
    assert "model_ready" in data["checks"]
    assert "research_ready" in data["checks"]
