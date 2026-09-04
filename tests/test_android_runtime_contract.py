"""
Tests des contrats d'exécution et de transport entre le client mobile Android et le backend E-ZzIO.
"""
from fastapi.testclient import TestClient
import pytest
from web_server import app

@pytest.fixture
def client():
    return TestClient(app)

def test_mobile_contract_health(client):
    """Le client Android doit pouvoir pinger le endpoint /health."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") in ["ok", "healthy"] or "status" in data

def test_mobile_contract_office_state(client):
    """Le client Android doit pouvoir interroger l'état de l'AI Office."""
    response = client.get("/master/api/v1/office/state")
    assert response.status_code == 200
    data = response.json()
    assert "rooms" in data
    assert "agents" in data
    assert len(data["rooms"]) == 8
    assert len(data["agents"]) == 10

def test_mobile_contract_hitl_pending_and_decide(client):
    """Le client Android doit pouvoir récupérer et arbitrer les demandes HITL."""
    # 1. Vérifier la récupération des approbations en attente
    res_pending = client.get("/master/api/v1/approvals/pending")
    assert res_pending.status_code == 200
    data = res_pending.json()
    assert "pending_approvals" in data
    assert "total" in data

    # 2. Vérifier que la décision sur une demande inexistante retourne bien 404 (non-crash)
    res_decide = client.post("/master/api/v1/approvals/non_existent_approval_id/decide", json={
        "decision": "APPROVE",
        "decided_by": "android_operator",
        "reason": "Validation mobile test"
    })
    assert res_decide.status_code == 404
