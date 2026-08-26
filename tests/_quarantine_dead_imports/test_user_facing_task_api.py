import pytest
from fastapi.testclient import TestClient
from interfaces.api.server import app

@pytest.fixture
def client():
    return TestClient(app)

def test_task_api_lifecycle_full_flow(client):
    # 1. Création de la tâche
    create_resp = client.post("/api/v1/tasks/", json={
        "objective": "Analyse structurée des composants",
        "session_id": "SESS_TASK_API_001",
        "max_steps": 3
    })
    assert create_resp.status_code == 200
    task_data = create_resp.json()
    t_id = task_data["task_id"]
    assert task_data["status"] == "CREATED"
    
    # 2. Récupération de l'état
    get_resp = client.get(f"/api/v1/tasks/{t_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["task_id"] == t_id
    
    # 3. Exécution de la tâche
    run_resp = client.post(f"/api/v1/tasks/{t_id}/run")
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["status"] == "COMPLETED"
    assert run_data["result"]["verified"] is True

def test_task_api_cancellation(client):
    create_resp = client.post("/api/v1/tasks/", json={
        "objective": "Tâche à annuler",
        "session_id": "SESS_CANCEL_001"
    })
    t_id = create_resp.json()["task_id"]
    
    cancel_resp = client.post(f"/api/v1/tasks/{t_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"

def test_task_api_nonexistent_task_404(client):
    resp = client.get("/api/v1/tasks/task_nonexistent_xyz")
    assert resp.status_code == 404
