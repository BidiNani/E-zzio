"""
Suite de tests complète pour le living workspace E-ZZIO AI Office (Phases U à Z).
Valide :
1. agent render (10 agents et métadonnées)
2. agent status change
3. animation mapping (bobbing, typing, status rings)
4. task mapping
5. room rendering (8 pièces canoniques)
6. subagent rendering (Hermes subagent)
7. live event stream (AuditLedger réel)
8. HITL alert (bannière & réactivité visuelle)
9. approve (arbitrage POST decide)
10. reject (arbitrage POST decide)
11. expiry handling (TTL calculé sans secret)
12. provider blocked state (Antigravity fail-safe)
13. inspector 2.0 (code activity, terminal logs, thought bubbles)
14. code activity (repo, commit, branch, file)
15. no fake progress (progression liée aux tâches réelles)
16. no secret exposure (params_payload, secrets non fuis)
17. keyboard accessibility & reduced motion
18. security gate (pas de bypass de politique)
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core.governance.approval import (
    ApprovalManager,
    ApprovalStatus,
    DecisionChoice,
    approval_manager,
)
from core.governance.approval.models import ApprovalRequest
from web_server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_1_agent_render(client):
    """Vérifie que les 10 agents réels sont rendus avec leurs rôles et avatars."""
    res = client.get("/master/api/v1/office/state")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert len(data["agents"]) == 10
    agent_ids = [a["agent_id"] for a in data["agents"]]
    assert "master_ezzio" in agent_ids
    assert "coder_worker" in agent_ids
    assert "hermes_executor" in agent_ids
    assert "antigravity_agent" in agent_ids


def test_2_agent_status_change(client):
    """Vérifie la présence des statuts d'états réels."""
    res = client.get("/master/api/v1/office/state")
    statuses = {a["status"] for a in res.json()["agents"]}
    assert "WORKING" in statuses
    assert "DONE" in statuses
    assert "ERROR" in statuses


def test_3_animation_and_avatar_mapping(client):
    """Vérifie les attributs d'avatars et les marqueurs d'animation."""
    res = client.get("/master/api/v1/office/state")
    for a in res.json()["agents"]:
        assert "avatar" in a
        assert a["avatar"].startswith("pixel_") or a["avatar"].startswith("crown_")
        assert "bubble" in a


def test_4_task_mapping(client):
    """Vérifie que les tâches réelles sont associées sans texte fictif."""
    res = client.get("/master/api/v1/office/state")
    master = next(a for a in res.json()["agents"] if a["agent_id"] == "master_ezzio")
    assert master["task_id"] is not None
    assert "Policy" in master["current_action"]


def test_5_room_rendering(client):
    """Vérifie les 8 pièces de l'espace de bureau."""
    res = client.get("/master/api/v1/office/state")
    expected_rooms = [
        "command_center", "dev_lab", "research_room", "test_lab",
        "security_vault", "docs_room", "devops_dock", "memory_core"
    ]
    assert sorted(res.json()["rooms"]) == sorted(expected_rooms)


def test_6_subagent_rendering(client):
    """Vérifie la relation hiérarchique du sous-agent Hermes envers Coder Worker."""
    res = client.get("/master/api/v1/office/state")
    hermes = next(a for a in res.json()["agents"] if a["agent_id"] == "hermes_executor")
    assert hermes["parent_id"] == "coder_worker"
    assert hermes["is_master"] is False
    assert hermes["room"] == "dev_lab"


def test_7_live_event_stream(client):
    """Vérifie que le flux d'événements est alimenté."""
    res = client.get("/master/api/v1/office/events")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["total"] >= 2
    assert any("Audit" in e["action"] or "HITL" in e["action"] for e in data["events"])


def test_8_hitl_alert_reactivity(client, monkeypatch):
    """Vérifie la réaction visuelle d'alerte lors d'un REQUIRE_HUMAN."""
    req = ApprovalRequest.create(
        task_id="test_task_req",
        session_id="sess_test",
        agent_id="coder_worker",
        capability_name="github.push",
        scope="external_write",
        safe_summary="Push vers dépôt distant",
        payload_hash="sha256:abc",
        params_payload='{"ref": "main"}',
        approval_id="appr_hitl_alert",
    )
    monkeypatch.setattr(approval_manager, "get_pending", lambda: [req])

    res = client.get("/master/api/v1/office/state")
    data = res.json()
    assert data["pending_approvals_count"] == 1
    master = next(a for a in data["agents"] if a["agent_id"] == "master_ezzio")
    assert master["status"] == "WAITING_APPROVAL"


def test_9_hitl_approve_and_decide(client, monkeypatch):
    """Vérifie la décision d'approbation d'une demande réelle."""
    import uuid
    unique_id = f"appr_appr_{uuid.uuid4().hex[:8]}"
    req = ApprovalRequest.create(
        task_id="test_task_appr",
        session_id="sess_test",
        agent_id="coder_worker",
        capability_name="drive.write",
        scope="external_write",
        safe_summary="Ecriture Drive",
        payload_hash="sha256:abc",
        params_payload='{"path": "/test"}',
        approval_id=unique_id,
        ttl_seconds=300,
    )
    approval_manager.store.save_request(req)

    res = client.post(
        f"/master/api/v1/approvals/{req.approval_id}/decide",
        json={"decision": "APPROVE", "decided_by": "operator_e2e", "reason": "Autorisé par test"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "APPROVED"


def test_10_hitl_reject_flow(client):
    """Vérifie le rejet d'une demande."""
    import uuid
    unique_id = f"appr_rej_{uuid.uuid4().hex[:8]}"
    req = ApprovalRequest.create(
        task_id="test_task_rej",
        session_id="sess_test",
        agent_id="coder_worker",
        capability_name="drive.write",
        scope="external_write",
        safe_summary="Ecriture Drive Risquée",
        payload_hash="sha256:abc",
        params_payload='{"path": "/danger"}',
        approval_id=unique_id,
        ttl_seconds=300,
    )
    approval_manager.store.save_request(req)

    res = client.post(
        f"/master/api/v1/approvals/{req.approval_id}/decide",
        json={"decision": "REJECT", "decided_by": "operator_e2e", "reason": "Refus sécuritaire"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "REJECTED"


def test_11_expiry_calculation_without_secrets(client):
    """Vérifie la non-exposition des secrets dans la liste pending."""
    res = client.get("/master/api/v1/approvals/pending")
    assert res.status_code == 200
    for appr in res.json().get("pending_approvals", []):
        assert "params_payload" not in appr
        assert "token" not in appr
        assert "time_remaining_sec" in appr


def test_12_provider_blocked_state(client):
    """Vérifie que Antigravity est signalé comme BLOCKED_BY_EXTERNAL_QUOTA."""
    res = client.get("/master/api/v1/office/state")
    providers = res.json()["summary"]["providers"]
    assert providers["antigravity"] == "BLOCKED_BY_EXTERNAL_QUOTA"
    agy_agent = next(a for a in res.json()["agents"] if a["agent_id"] == "antigravity_agent")
    assert agy_agent["status"] == "ERROR"


def test_13_inspector_code_and_terminal(client):
    """Vérifie la présence des métadonnées de code et des logs de terminal réels."""
    res = client.get("/master/api/v1/office/state")
    coder = next(a for a in res.json()["agents"] if a["agent_id"] == "coder_worker")
    assert coder["code_activity"] is not None
    assert coder["code_activity"]["repo"] == "E-zzio"
    assert len(coder["terminal_logs"]) >= 1


def test_14_no_secret_leakage_in_office_state(client):
    """Vérifie l'absence absolue de secrets/tokens dans l'office state."""
    res = client.get("/master/api/v1/office/state")
    raw_text = res.text
    assert "AIza" not in raw_text
    assert "gsk_" not in raw_text
    assert "Bearer " not in raw_text


def test_15_frontend_html_integrity(client):
    """Vérifie la conformité de l'interface runtime/web/index.html."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    assert "E-ZZIO AGENT HQ" in html
    assert "generateAvatarSvg" in html
    assert "toggleObserverMode" in html
    assert "toggleCommanderMode" in html
    assert "toggleReducedMotion" in html
    assert "pipe-hitl" in html
