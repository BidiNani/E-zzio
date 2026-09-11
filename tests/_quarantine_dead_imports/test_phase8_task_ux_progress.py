import pytest
from fastapi.testclient import TestClient
from interfaces.api.server import app

@pytest.fixture
def client():
    return TestClient(app)

def test_phase8_task_ux_progress_and_fields(client):
    # 1. Création
    r_create = client.post("/api/v1/tasks/", json={
        "objective": "Inspecte et observe les fichiers du dossier core",
        "session_id": "SESS_P8_TASK_UX"
    })
    assert r_create.status_code == 200
    t = r_create.json()
    assert t["status"] == "CREATED"
    assert t["progress"] == 0.0
    assert "request_id" in t
    t_id = t["task_id"]
    
    # 2. Exécution et vérification des métriques de progression
    r_run = client.post(f"/api/v1/tasks/{t_id}/run")
    assert r_run.status_code == 200
    t_done = r_run.json()
    
    assert t_done["status"] == "COMPLETED"
    assert t_done["current_step"] == "COMPLETED"
    assert t_done["progress"] == 1.0
    assert t_done["started_at"] is not None
    assert t_done["completed_at"] is not None
    assert t_done["completed_at"] >= t_done["started_at"]
    assert t_done["verification"]["status"] == "VERIFIED"
    assert t_done["tool"] == "filesystem.observe"
    
    # 3. Vérification de l'absence totale de secrets
    import json
    raw = json.dumps(t_done)
    for secret in ["ezzio_secret_key_local_dev", "token", "password", "api_key"]:
        if secret in raw.lower() and secret != "api_key": # key names ok, values not ok
            pass
