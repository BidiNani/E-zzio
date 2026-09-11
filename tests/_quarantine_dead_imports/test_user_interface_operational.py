import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from interfaces.api.server import app

@pytest.fixture
def client():
    return TestClient(app)

def test_user_interface_root_and_hud_accessible(client):
    # 1. Accès à la racine
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "text/html" in res_root.headers.get("content-type", "")
    assert "E‑ZZIO" in res_root.text

    # 2. Accès au endpoint /hud
    res_hud = client.get("/hud")
    assert res_hud.status_code == 200
    assert "text/html" in res_hud.headers.get("content-type", "")

def test_user_interface_operational_chat_flow(client):
    # Simulation du flux utilisateur complet: 1er message -> réponse -> 2e message avec rappel
    mock_responses = [
        {"response": "Bienvenue ! Mon nom de code est E-ZZIO.", "intent": "chat", "provider": "ollama"},
        {"response": "Votre projet s'appelle E-ZZIO.", "intent": "chat", "provider": "ollama"}
    ]
    
    with patch("routers.chat._core.think", new_callable=AsyncMock) as mock_think:
        mock_think.side_effect = mock_responses
        
        # Premier message
        resp1 = client.post("/api/v1/chat/", json={
            "message": "Bonjour, quel est le projet ?",
            "user_id": "ui_human_user",
            "session_id": "SESS_UI_OPERATIONAL"
        })
        assert resp1.status_code == 200
        d1 = resp1.json()
        assert "E-ZZIO" in d1["response"]
        assert d1["session_id"] == "SESS_UI_OPERATIONAL"
        
        # Deuxième message
        resp2 = client.post("/api/v1/chat/", json={
            "message": "Rappelle-moi le nom.",
            "user_id": "ui_human_user",
            "session_id": "SESS_UI_OPERATIONAL"
        })
        assert resp2.status_code == 200
        d2 = resp2.json()
        assert "E-ZZIO" in d2["response"]
