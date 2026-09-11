"""
Suite de tests pour le CLI Human-in-the-Loop (tools/ezzio_approval.py).
Valide :
- list (vide et avec éléments)
- approve
- reject
- expiration
- ID inconnu
- double décision (conflit)
"""
import io
import sqlite3
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import pytest

from core.governance.approval import (
    ApprovalManager,
    ApprovalStatus,
    DecisionChoice,
)
from core.governance.approval.store import SqliteApprovalStore
from core.security.audit_ledger import AuditLedger
from core.tasks import manager as task_manager_mod
import tools.ezzio_approval as cli_mod


@pytest.fixture
def cli_env(tmp_path: Path, monkeypatch):
    tasks_db_path = tmp_path / "cli_tasks.db"
    audit_db_path = tmp_path / "cli_audit.db"

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

    monkeypatch.setattr(cli_mod, "approval_manager", mgr)

    return {
        "manager": mgr,
        "tasks_db": tasks_db_path,
        "task_manager": tm,
    }


def test_cli_list_empty(cli_env):
    """Vérifie la commande list quand aucune approbation n'est en attente."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        ret = cli_mod.cmd_list(None)
    assert ret == 0
    assert "Aucune demande d'approbation en attente" in buf.getvalue()


def test_cli_list_with_items_no_secret(cli_env):
    """Vérifie la commande list avec éléments sans afficher de secrets."""
    mgr: ApprovalManager = cli_env["manager"]
    mgr.request_approval(
        task_id="tsk_cli_1",
        session_id="sess_1",
        agent_id="coding_worker",
        capability_name="google-drive-mcp",
        scope="drive.write",
        safe_summary="Upload file confidential.pdf",
        params={"raw_token": "SECRET_SHOULD_NOT_LEAK"},
    )

    buf = io.StringIO()
    with redirect_stdout(buf):
        ret = cli_mod.cmd_list(None)
    assert ret == 0
    out = buf.getvalue()
    assert "drive.write" in out
    assert "Upload file confidential.pdf" in out
    assert "SECRET_SHOULD_NOT_LEAK" not in out


def test_cli_approve(cli_env):
    """Vérifie la commande approve."""
    mgr: ApprovalManager = cli_env["manager"]
    req = mgr.request_approval(
        task_id="tsk_cli_2",
        session_id="sess_2",
        agent_id="coding_worker",
        capability_name="github-mcp",
        scope="github.push",
        safe_summary="Push main branch",
        params={},
    )

    class MockArgs:
        approval_id = req.approval_id
        by = "bob"
        reason = "Validation manuelle CLI"

    buf = io.StringIO()
    with redirect_stdout(buf):
        ret = cli_mod.cmd_approve(MockArgs())
    assert ret == 0
    assert "APPROUVÉE avec succès par bob" in buf.getvalue()

    updated = mgr.get(req.approval_id)
    assert updated.status == ApprovalStatus.APPROVED


def test_cli_reject(cli_env):
    """Vérifie la commande reject."""
    mgr: ApprovalManager = cli_env["manager"]
    req = mgr.request_approval(
        task_id="tsk_cli_3",
        session_id="sess_3",
        agent_id="coding_worker",
        capability_name="system-mcp",
        scope="system.destructive",
        safe_summary="rm files",
        params={},
    )

    class MockArgs:
        approval_id = req.approval_id
        by = "security_lead"
        reason = "Destruction refusée"

    buf = io.StringIO()
    with redirect_stdout(buf):
        ret = cli_mod.cmd_reject(MockArgs())
    assert ret == 0
    assert "REJETÉE avec succès par security_lead" in buf.getvalue()

    updated = mgr.get(req.approval_id)
    assert updated.status == ApprovalStatus.REJECTED


def test_cli_unknown_id(cli_env):
    """Vérifie qu'un ID inconnu renvoie le code d'erreur approprié."""
    class MockArgs:
        approval_id = "appr_does_not_exist"
        by = "bob"
        reason = "None"

    buf_err = io.StringIO()
    with redirect_stderr(buf_err):
        ret = cli_mod.cmd_approve(MockArgs())
    assert ret == 1
    assert "Demande inconnue" in buf_err.getvalue()


def test_cli_expired(cli_env):
    """Vérifie le traitement d'une approbation expirée dans le CLI."""
    mgr: ApprovalManager = cli_env["manager"]
    tasks_db = cli_env["tasks_db"]

    req = mgr.request_approval(
        task_id="tsk_cli_4",
        session_id="sess_4",
        agent_id="coding_worker",
        capability_name="c",
        scope="s",
        safe_summary="s",
        params={},
    )

    with sqlite3.connect(tasks_db) as conn:
        conn.execute("UPDATE approval_requests SET expires_at = '2000-01-01T00:00:00+00:00' WHERE approval_id = ?", (req.approval_id,))

    class MockArgs:
        approval_id = req.approval_id
        by = "bob"
        reason = "Trop tard"

    buf_err = io.StringIO()
    with redirect_stderr(buf_err):
        ret = cli_mod.cmd_approve(MockArgs())
    assert ret == 2
    assert "expiré" in buf_err.getvalue().lower()


def test_cli_double_decision(cli_env):
    """Vérifie le blocage d'une double décision sur la même demande."""
    mgr: ApprovalManager = cli_env["manager"]
    req = mgr.request_approval(
        task_id="tsk_cli_5",
        session_id="sess_5",
        agent_id="coding_worker",
        capability_name="c",
        scope="s",
        safe_summary="s",
        params={},
    )

    class MockArgs:
        approval_id = req.approval_id
        by = "bob"
        reason = "Premier avis"

    cli_mod.cmd_approve(MockArgs())

    # Deuxième tentative
    buf_err = io.StringIO()
    with redirect_stderr(buf_err):
        ret = cli_mod.cmd_reject(MockArgs())
    assert ret == 3
    assert "CONFLIT" in buf_err.getvalue()
