import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from v17.api.router import router
from v17.control.service import human_control_plane
from v17.control.models import RiskLevel, ActionStatus

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_v17_4_action_read_only_auto_approved():
    res = client.post("/api/v17/product/actions", json={
        "action_type": "GET_SYSTEM_STATE",
        "target": "system",
        "parameters": {}
    })
    assert res.status_code == 200
    data = res.json()
    assert data["risk_level"] == "READ_ONLY"
    assert data["status"] == "VERIFIED"
    assert data["result"]["readiness"] == "READY"

def test_v17_4_action_high_risk_requires_confirmation_and_approve():
    # 1. Create high risk action
    res = client.post("/api/v17/product/actions", json={
        "action_type": "REQUEST_TASK_CANCEL",
        "target": "task_123",
        "parameters": {}
    })
    assert res.status_code == 200
    data = res.json()
    req_id = data["request_id"]
    assert data["risk_level"] == "HIGH"
    assert data["confirmation_required"] is True
    assert data["status"] == "AWAITING_CONFIRMATION"

    # 2. Approve action
    res_appr = client.post(f"/api/v17/product/actions/{req_id}/approve")
    assert res_appr.status_code == 200
    data_appr = res_appr.json()
    assert data_appr["status"] == "VERIFIED"
    assert data_appr["result"]["status"] == "CANCELLED_SAFE"

def test_v17_4_action_deny():
    res = client.post("/api/v17/product/actions", json={
        "action_type": "EMERGENCY_SHUTDOWN",
        "target": "all",
        "parameters": {}
    })
    req_id = res.json()["request_id"]
    res_deny = client.post(f"/api/v17/product/actions/{req_id}/deny?reason=Accidental+trigger")
    assert res_deny.status_code == 200
    assert res_deny.json()["status"] == "DENIED"

def test_v17_4_idempotency_guarantee():
    key = "idem_key_unique_test_1"
    res1 = client.post("/api/v17/product/actions", json={
        "action_type": "GET_SYSTEM_STATE",
        "target": "system",
        "idempotency_key": key
    })
    res2 = client.post("/api/v17/product/actions", json={
        "action_type": "GET_SYSTEM_STATE",
        "target": "system",
        "idempotency_key": key
    })
    assert res1.json()["request_id"] == res2.json()["request_id"]

def test_v17_4_adversarial_security_no_secret_leak():
    res = client.post("/api/v17/product/actions", json={
        "action_type": "GET_SYSTEM_STATE",
        "target": "system",
        "parameters": {
            "DISCORD_TOKEN": "123456789.abc.def",
            "GEMINI_API_KEY": "AIzaSyD-secret-key"
        }
    })
    data = res.json()
    assert data["parameters"]["DISCORD_TOKEN"] == "[REDACTED]"
    assert data["parameters"]["GEMINI_API_KEY"] == "[REDACTED]"
