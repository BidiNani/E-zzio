"""
Suite de tests pour l'API REST FastAPI Human-in-the-Loop (HITL).
Valide :
- GET /api/v1/approvals/pending (liste, assainissement sans secrets)
- POST /api/v1/approvals/{id}/decide (APPROVE, REJECT, cas d'erreur)
- Gestion des erreurs : inconnu (404), expiré (410), conflit/déjà décidé (409), décision invalide (422)
- Non-exposition des secrets
"""
import sqlite3
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.governance.approval import (
    ApprovalManager,
    ApprovalStatus,
    DecisionChoice,
)
from core.governance.approval.store import SqliteApprovalStore
from core.security.audit_ledger import AuditLedger
from core.tasks import manager as task_manager_mod
from routers.approval import router as approval_router
import routers.approval as approval_router_mod


@pytest.fixture
def api_client(tmp_path: Path, monkeypatch):
    """Initialise un client FastAPI de test avec base de données isolée."""
    tasks_db_path = tmp_path / "api_tasks.db"
    audit_db_path = tmp_path / "api_audit.db"

    # Créer table governed_tasks
    with sqlite3.connect(tasks_db_path) as conn:
        conn.execute("""
            CREATE TABLE governed_tasks (
                task_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                workspace TEXT NOT NULL,
                state TEXT NOT NULL,
                scope_json TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                approval_id TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

    monkeypatch.setattr(task_manager_mod, "DB_PATH", tasks_db_path)
    tm = task_manager_mod.TaskManager()
    monkeypatch.setattr(task_manager_mod, "task_manager", tm)

    store = SqliteApprovalStore(db_path=tasks_db_path)
    ledger = AuditLedger(db_path=str(audit_db_path))
    mgr = ApprovalManager(store=store, audit_ledger=ledger)

    # Monkeypatch de l'instance approval_manager dans le routeur
    monkeypatch.setattr(approval_router_mod, "approval_manager", mgr)

    # Créer l'application FastAPI de test
    app = FastAPI()
    app.include_router(approval_router)
    client = TestClient(app)

    return {
        "client": client,
        "manager": mgr,
        "tasks_db": tasks_db_path,
        "task_manager": tm,
    }


def test_api_pending_list_empty(api_client):
    """Vérifie le retour d'une liste vide si aucune demande."""
    client: TestClient = api_client["client"]
    resp = client.get("/api/v1/approvals/pending")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["pending_approvals"] == []
    assert data["total"] == 0


def test_api_pending_list_with_items_no_secrets(api_client):
    """Vérifie que la liste retourne les informations nécessaires sans exposer le payload secret."""
    client: TestClient = api_client["client"]
    mgr: ApprovalManager = api_client["manager"]

    mgr.request_approval(
        task_id="tsk_api_1",
        session_id="sess_1",
        agent_id="agent_1",
        capability_name="google-drive-mcp",
        scope="drive.write",
        safe_summary="Téléchargement du contrat client",
        params={"api_key": "SECRET_KEY_DO_NOT_EXPOSE", "file_data": "CONFIDENTIAL"},
    )

    resp = client.get("/api/v1/approvals/pending")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    item = data["pending_approvals"][0]
    assert item["capability_name"] == "google-drive-mcp"
    assert item["scope"] == "drive.write"
    assert item["safe_summary"] == "Téléchargement du contrat client"
    assert item["status"] == "PENDING"
    assert item["time_remaining_sec"] > 0

    # NON-EXPOSITION DES SECRETS
    raw_text = resp.text
    assert "SECRET_KEY_DO_NOT_EXPOSE" not in raw_text
    assert "CONFIDENTIAL" not in raw_text
    assert "params_payload" not in item


def test_api_approve_valid(api_client):
    """Vérifie l'approbation via l'endpoint POST decide."""
    client: TestClient = api_client["client"]
    mgr: ApprovalManager = api_client["manager"]

    req = mgr.request_approval(
        task_id="tsk_api_2",
        session_id="sess_2",
        agent_id="agent_2",
        capability_name="github-mcp",
        scope="github.push",
        safe_summary="Push main",
        params={"branch": "main"},
    )

    resp = client.post(
        f"/api/v1/approvals/{req.approval_id}/decide",
        json={"decision": "APPROVE", "decided_by": "alice", "reason": "Code vérifié"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["status"] == "APPROVED"
    assert data["decided_by"] == "alice"


def test_api_reject_valid(api_client):
    """Vérifie le rejet via l'endpoint POST decide."""
    client: TestClient = api_client["client"]
    mgr: ApprovalManager = api_client["manager"]

    req = mgr.request_approval(
        task_id="tsk_api_3",
        session_id="sess_3",
        agent_id="agent_3",
        capability_name="system-mcp",
        scope="system.destructive",
        safe_summary="Delete files",
        params={},
    )

    resp = client.post(
        f"/api/v1/approvals/{req.approval_id}/decide",
        json={"decision": "REJECT", "decided_by": "security_officer", "reason": "Non autorisé"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["status"] == "REJECTED"


def test_api_unknown_approval_404(api_client):
    """Vérifie qu'un ID inconnu renvoie 404."""
    client: TestClient = api_client["client"]
    resp = client.post(
        "/api/v1/approvals/appr_nonexistent/decide",
        json={"decision": "APPROVE", "decided_by": "alice"},
    )
    assert resp.status_code == 404


def test_api_expired_approval_410(api_client):
    """Vérifie qu'une demande expirée renvoie 410 Gone."""
    client: TestClient = api_client["client"]
    mgr: ApprovalManager = api_client["manager"]
    tasks_db = api_client["tasks_db"]

    req = mgr.request_approval(
        task_id="tsk_api_4",
        session_id="sess_4",
        agent_id="agent_4",
        capability_name="c",
        scope="s",
        safe_summary="s",
        params={},
    )

    # Forcer l'expiration
    with sqlite3.connect(tasks_db) as conn:
        conn.execute("UPDATE approval_requests SET expires_at = '2000-01-01T00:00:00+00:00' WHERE approval_id = ?", (req.approval_id,))

    resp = client.post(
        f"/api/v1/approvals/{req.approval_id}/decide",
        json={"decision": "APPROVE", "decided_by": "alice"},
    )
    assert resp.status_code == 410


def test_api_already_decided_409(api_client):
    """Vérifie qu'une seconde décision sur une demande déjà traitée renvoie 409 Conflict."""
    client: TestClient = api_client["client"]
    mgr: ApprovalManager = api_client["manager"]

    req = mgr.request_approval(
        task_id="tsk_api_5",
        session_id="sess_5",
        agent_id="agent_5",
        capability_name="c",
        scope="s",
        safe_summary="s",
        params={},
    )

    # 1ère décision
    client.post(
        f"/api/v1/approvals/{req.approval_id}/decide",
        json={"decision": "APPROVE", "decided_by": "alice"},
    )

    # 2ème décision
    resp2 = client.post(
        f"/api/v1/approvals/{req.approval_id}/decide",
        json={"decision": "APPROVE", "decided_by": "alice"},
    )
    assert resp2.status_code == 409


def test_api_invalid_decision_422(api_client):
    """Vérifie qu'une valeur de décision invalide (ex: FORCED_STATUS, EXPIRED) renvoie 422 Unprocessable Entity."""
    client: TestClient = api_client["client"]
    mgr: ApprovalManager = api_client["manager"]

    req = mgr.request_approval(
        task_id="tsk_api_6",
        session_id="sess_6",
        agent_id="agent_6",
        capability_name="c",
        scope="s",
        safe_summary="s",
        params={},
    )

    resp = client.post(
        f"/api/v1/approvals/{req.approval_id}/decide",
        json={"decision": "CONSUMED", "decided_by": "hacker"},
    )
    assert resp.status_code == 422
