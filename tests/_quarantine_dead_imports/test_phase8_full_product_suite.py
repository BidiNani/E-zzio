import pytest
import subprocess
import sys
from fastapi.testclient import TestClient
from interfaces.api.server import app

@pytest.fixture
def client():
    return TestClient(app)

def test_phase8_hud_and_control_plane_live_integration(client):
    # 1. Vivacité et état des composants
    resp_ready = client.get("/api/v1/health/readiness")
    assert resp_ready.status_code == 200
    ready_data = resp_ready.json()
    assert "status" in ready_data
    
    # 2. Accès HUD
    resp_hud = client.get("/hud")
    assert resp_hud.status_code == 200
    assert "E‑ZZIO" in resp_hud.text

def test_phase8_user_facing_error_handling_no_traceback_leak(client):
    # Tâche inexistante -> erreur structurée 404
    resp = client.get("/api/v1/tasks/task_invalid_xyz_000")
    assert resp.status_code == 404
    data = resp.json()
    assert "detail" in data
    # Vérification d'absence de stacktrace brute
    assert "Traceback" not in str(data)

def test_phase8_real_one_command_product_lifecycle():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    start_script = root / "scripts" / "start_ezzio.py"
    stop_script = root / "scripts" / "stop_ezzio.py"
    
    # START -> READY
    p_start = subprocess.run([sys.executable, str(start_script)], capture_output=True, text=True)
    assert p_start.returncode == 0
    assert "E-ZZIO READY" in p_start.stdout
    
    # SHUTDOWN
    p_stop = subprocess.run([sys.executable, str(stop_script)], capture_output=True, text=True)
    assert p_stop.returncode == 0
    assert "ARRET DU SYSTEME" in p_stop.stdout
