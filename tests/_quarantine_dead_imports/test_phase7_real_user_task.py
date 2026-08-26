import pytest
from fastapi.testclient import TestClient
from interfaces.api.server import app

@pytest.fixture
def client():
    return TestClient(app)

def test_phase7_real_user_task_e2e_run(client):
    # 1. Création de la tâche utilisateur réelle
    req_body = {
        "objective": "Inspecte le dossier core et résume les composants",
        "session_id": "SESS_PHASE7_USER_TASK",
        "max_steps": 3
    }
    create_res = client.post("/api/v1/tasks/", json=req_body)
    assert create_res.status_code == 200
    t_id = create_res.json()["task_id"]
    
    # 2. Exécution réelle de la tâche
    run_res = client.post(f"/api/v1/tasks/{t_id}/run")
    assert run_res.status_code == 200
    data = run_res.json()
    
    assert data["status"] == "COMPLETED"
    assert data["result"]["verified"] is True
    assert "observation" in data["result"]
    assert data["result"]["observation"]["status"] == "SUCCESS"
    assert data["result"]["observation"]["total_files"] > 0
    assert data["result"]["ledger_events"] > 0
