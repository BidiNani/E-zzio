"""
Tests pour le sous-système E-ZZIO AI Office (Virtual Workspace).
Valide :
- GET /master/api/v1/office/state (10 agents réels, 8 pièces, statistiques de santé)
- GET /master/api/v1/office/events (flux d'événements temps réel)
- Réactivité HITL : bascule de l'état visuel en WAITING_APPROVAL si une approbation est en attente
- Statut de fail-safe Antigravity : BLOCKED_BY_EXTERNAL_QUOTA
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core.governance.approval import (
    ApprovalManager,
    ApprovalStatus,
    approval_manager,
)
from core.governance.approval.models import ApprovalRequest
from web_server import app


def test_office_state_returns_200_and_sovereign_authority(client):
    res = client.get("/master/api/v1/office/state")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "E-ZZIO" in data["master_authority"]
    assert len(data["rooms"]) == 8
    assert len(data["agents"]) == 10


def test_office_state_contains_all_rooms(client):
    res = client.get("/master/api/v1/office/state")
    data = res.json()
    expected_rooms = {
        "command_center",
        "dev_lab",
        "research_room",
        "test_lab",
        "security_vault",
        "docs_room",
        "devops_dock",
        "memory_core",
    }
    assert set(data["rooms"]) == expected_rooms


def test_office_state_agent_hierarchy(client):
    res = client.get("/master/api/v1/office/state")
    agents = {a["agent_id"]: a for a in res.json()["agents"]}

    # Master Governor
    assert agents["master_ezzio"]["is_master"] is True
    assert agents["master_ezzio"]["parent_id"] is None
    assert agents["master_ezzio"]["room"] == "command_center"

    # Hermes subagent belongs to dev_lab and child of coder_worker
    assert agents["hermes_executor"]["parent_id"] == "coder_worker"
    assert agents["hermes_executor"]["room"] == "dev_lab"

    # Antigravity is quota blocked fail-safe
    assert agents["antigravity_agent"]["status"] == "ERROR"
    assert "BLOCKED_BY_EXTERNAL_QUOTA" in agents["antigravity_agent"]["last_event"]


def test_office_state_provider_statuses(client):
    res = client.get("/master/api/v1/office/state")
    providers = res.json()["summary"]["providers"]
    assert providers["gemini"] == "PASS"
    assert providers["groq"] == "PASS"
    assert providers["ollama"] == "PASS"
    assert providers["antigravity"] == "BLOCKED_BY_EXTERNAL_QUOTA"


def test_office_live_events_stream(client):
    res = client.get("/master/api/v1/office/events")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["total"] >= 5
    assert any("Audit" in e["action"] or "HITL" in e["action"] for e in data["events"])


def test_office_state_reacts_to_pending_approval(client, monkeypatch):
    # Simuler une approbation en attente
    dummy_req = ApprovalRequest.create(
        task_id="task_visual_test",
        session_id="sess_001",
        agent_id="coder_worker",
        capability_name="drive.write",
        scope="external_write",
        safe_summary="Ecriture externe vers Drive",
        payload_hash="sha256:dummy",
        params_payload='{"path": "/remote/test.txt"}',
        approval_id="appr_visual_test",
    )

    monkeypatch.setattr(approval_manager, "get_pending", lambda: [dummy_req])

    res = client.get("/master/api/v1/office/state")
    assert res.status_code == 200
    data = res.json()

    assert data["pending_approvals_count"] == 1
    agents = {a["agent_id"]: a for a in data["agents"]}
    # Master and Security guard react visually to pending approvals
    assert agents["master_ezzio"]["status"] == "WAITING_APPROVAL"
    assert agents["sec_guard"]["status"] == "WAITING_APPROVAL"
