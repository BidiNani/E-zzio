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
    payload = {
        "message": "Bonjour E-ZZIO",
        "user_id": "test_user_01"
    }
    mock_result = {
        "response": "Bonjour ! Prêt à exécuter vos ordres.",
        "intent": "local_chat",
        "provider": "ollama",
        "mode": "local_chat",
        "session_id": "sess_test_user_01",
        "data": {}
    }
    with patch("routers.chat._core.think", new_callable=AsyncMock) as mock_think:
        mock_think.return_value = mock_result
        resp = client.post("/api/v1/chat", json=payload)
        
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "local_chat"
        assert data["provider"] == "ollama"
        assert "Bonjour" in data["response"]
