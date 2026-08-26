import pytest
from starlette.testclient import TestClient
from interfaces.api.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_system_status_endpoint(client):
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "E-ZZIO OS"
    assert data["status"] == "ONLINE"
    assert "memory" in data
    assert "total_gb" in data["memory"]
    assert data["websockets_ready"] is True


def test_websocket_chat_streaming(client):
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"message": "Bonjour E-zzio", "session_id": "sess_test_123"})
        
        # 1. Statut initial
        status_msg = websocket.receive_json()
        assert status_msg["type"] == "status"
        assert status_msg["status"] == "processing"
        
        # 2. Réception des tokens
        tokens = []
        while True:
            msg = websocket.receive_json()
            if msg["type"] == "done":
                assert msg["status"] == "completed"
                break
            elif msg["type"] == "token":
                tokens.append(msg["token"])
        
        full_text = "".join(tokens)
        assert "E-ZZIO" in full_text
        assert "Bonjour E-zzio" in full_text
