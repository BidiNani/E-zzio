"""
E-ZZIO V9.4 — Living AI Office Motion & 2.5D Simulation Test Suite.
Verifies deterministic pathfinding, agent-state to animation mapping,
spatial room routing, collision avoidance, and HITL movement triggers.
"""
import math
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core.governance.approval import approval_manager
from core.governance.approval.models import ApprovalRequest
from web_server import app

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_office_map_endpoint_returns_canonical_rooms(client):
    """Verify GET /master/api/v1/office/map returns 36x24 grid and all 8 rooms plus hub."""
    res = client.get("/master/api/v1/office/map")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["grid_width"] == 36
    assert data["grid_height"] == 24
    assert data["tile_size"] == 28

    expected_rooms = {
        "command_center", "dev_lab", "research_room", "test_lab",
        "central_hub", "security_vault", "docs_room", "devops_dock", "memory_core"
    }
    assert set(data["rooms"].keys()) == expected_rooms

    for _key, r in data["rooms"].items():
        assert "door" in r and "desk" in r
        assert r["w"] >= 8 and r["h"] >= 6
        assert r["color"].startswith("#")


def test_agent_visual_states_contain_spatial_coordinates(client):
    """Verify all 10 agents have valid non-null 2.5D spatial coordinates and animation states."""
    res = client.get("/master/api/v1/office/state")
    assert res.status_code == 200
    agents = res.json()["agents"]
    assert len(agents) == 10

    for a in agents:
        assert "x" in a and "y" in a
        assert 0 <= a["x"] <= 36
        assert 0 <= a["y"] <= 24
        assert a["heading"] in {"UP", "DOWN", "LEFT", "RIGHT"}
        assert a["animation_state"] in {"IDLE", "WALK", "WORK", "WAIT_APPROVAL", "ERROR", "DONE"}


def test_task_to_room_routing_contract(client):
    """Verify agents are correctly located at their designated specialty rooms."""
    res = client.get("/master/api/v1/office/state")
    agents = {a["agent_id"]: a for a in res.json()["agents"]}

    assert agents["master_ezzio"]["room"] == "command_center"
    assert agents["coder_worker"]["room"] == "dev_lab"
    assert agents["hermes_executor"]["room"] == "dev_lab"
    assert agents["researcher_scout"]["room"] == "research_room"
    assert agents["qa_tester"]["room"] == "test_lab"
    assert agents["sec_guard"]["room"] == "security_vault"
    assert agents["docs_scribe"]["room"] == "docs_room"
    assert agents["devops_dock"]["room"] == "devops_dock"
    assert agents["memory_archivist"]["room"] == "memory_core"
    assert agents["antigravity_agent"]["room"] == "dev_lab"


def test_hitl_interception_triggers_movement_to_command_center(client, monkeypatch):
    """Verify that when a pending approval exists, Aegis Guard routes to Command Center."""
    req = ApprovalRequest.create(
        task_id="task_motion_hitl",
        session_id="sess_motion",
        agent_id="coder_worker",
        capability_name="drive.write",
        scope="external_write",
        safe_summary="Demande de test pour mouvement HITL",
        payload_hash="sha256:motion_test",
        params_payload='{"path": "/tmp/test.txt"}',
        approval_id="appr_motion_hitl_01",
    )
    monkeypatch.setattr(approval_manager, "get_pending", lambda: [req])

    res = client.get("/master/api/v1/office/state")
    assert res.status_code == 200
    agents = {a["agent_id"]: a for a in res.json()["agents"]}

    # Aegis Guard doit être dirigé vers le Command Center
    sec = agents["sec_guard"]
    assert sec["status"] == "WAITING_APPROVAL"
    assert sec["target_room"] == "command_center"
    assert sec["animation_state"] == "WAIT_APPROVAL"
    assert sec["x"] == 7.0 and sec["y"] == 5.0

    # Master Governor doit être en alerte d'approbation
    master = agents["master_ezzio"]
    assert master["status"] == "WAITING_APPROVAL"
    assert master["animation_state"] == "WAIT_APPROVAL"


def test_antigravity_quota_standby_remains_stationary(client):
    """Verify Antigravity specialist is stationary in standby with ERROR state without fake work."""
    res = client.get("/master/api/v1/office/state")
    agents = {a["agent_id"]: a for a in res.json()["agents"]}
    agy = agents["antigravity_agent"]

    assert agy["status"] == "ERROR"
    assert agy["animation_state"] == "ERROR"
    assert agy["progress"] == 0
    assert "BLOCKED_BY_EXTERNAL_QUOTA" in agy["last_event"]
    assert agy["target_room"] is None


def test_multi_agent_spatial_separation_no_overlap(client):
    """Verify that distinct agents stationed at desks have non-overlapping coordinates (dist >= 1.0)."""
    res = client.get("/master/api/v1/office/state")
    agents = res.json()["agents"]

    for i in range(len(agents)):
        for j in range(i + 1, len(agents)):
            a1 = agents[i]
            a2 = agents[j]
            dist = math.hypot(a1["x"] - a2["x"], a1["y"] - a2["y"])
            assert dist >= 1.0, f"Agents {a1['agent_id']} and {a2['agent_id']} overlap at distance {dist}!"


def test_frontend_motion_and_canvas_scripts_served(client):
    """Verify ezzio-office-motion.js and ezzio-office-canvas.js are served over static route."""
    res_motion = client.get("/static/ezzio-office-motion.js")
    assert res_motion.status_code == 200
    assert "EzzioMotion" in res_motion.text
    assert "aStar" in res_motion.text

    res_canvas = client.get("/static/ezzio-office-canvas.js")
    assert res_canvas.status_code == 200
    assert "OfficeCanvas" in res_canvas.text
    assert "renderAgent" in res_canvas.text
