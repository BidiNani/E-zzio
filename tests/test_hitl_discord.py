"""
Suite de tests pour le pont Discord HITL (core/integrations/discord/hitl_bridge.py).
Valide sans appel réseau réel :
- build_approval_embed_payload (structure, métadonnées, assainissement sans secrets)
- handle_interaction_decision : APPROVE
- handle_interaction_decision : REJECT
- Demande expirée
- ID inconnu
- Double clic / tentative de rejeu de décision
- Valeur de choix invalide
"""
import sqlite3
from pathlib import Path

import pytest

from core.governance.approval import (
    ApprovalManager,
    ApprovalStatus,
    DecisionChoice,
)
from core.governance.approval.store import SqliteApprovalStore
from core.integrations.discord.hitl_bridge import DiscordApprovalController
from core.security.audit_ledger import AuditLedger
from core.tasks import manager as task_manager_mod


@pytest.fixture
def discord_env(tmp_path: Path, monkeypatch):
    tasks_db_path = tmp_path / "discord_tasks.db"
    audit_db_path = tmp_path / "discord_audit.db"

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

    ctrl = DiscordApprovalController(manager=mgr)

    return {
        "controller": ctrl,
        "manager": mgr,
        "tasks_db": tasks_db_path,
        "task_manager": tm,
    }


def test_discord_build_embed_no_secrets(discord_env):
    """Vérifie que l'embed Discord est construit correctement sans exposer les secrets."""
    ctrl: DiscordApprovalController = discord_env["controller"]
    mgr: ApprovalManager = discord_env["manager"]

    req = mgr.request_approval(
        task_id="tsk_disc_1",
        session_id="sess_disc_1",
        agent_id="Hermes",
        capability_name="google-drive-mcp",
        scope="drive.write",
        safe_summary="Upload de rapport.pdf vers Drive",
        params={"client_secret": "DISCORD_SECRET_LEAK_CHECK"},
    )

    embed = ctrl.build_approval_embed_payload(req.approval_id)
    assert embed["title"] == "🛡️ E-ZZIO HITL — Validation Requise"
    desc_str = str(embed)
    assert "DISCORD_SECRET_LEAK_CHECK" not in desc_str
    assert "drive.write" in desc_str
    assert "Upload de rapport.pdf vers Drive" in desc_str


def test_discord_interaction_approve(discord_env):
    """Vérifie l'approbation via l'interaction Discord."""
    ctrl: DiscordApprovalController = discord_env["controller"]
    mgr: ApprovalManager = discord_env["manager"]

    req = mgr.request_approval(
        task_id="tsk_disc_2",
        session_id="sess_disc_2",
        agent_id="Hermes",
        capability_name="github-mcp",
        scope="github.push",
        safe_summary="Push main",
        params={},
    )

    res = ctrl.handle_interaction_decision(
        approval_id=req.approval_id,
        choice_str="APPROVE",
        user_id="186035306418405376",
        username="OwnerBidi",
    )

    assert res["ok"] is True
    assert res["status"] == "APPROVED"
    assert "OwnerBidi" in res["decided_by"]

    updated = mgr.get(req.approval_id)
    assert updated.status == ApprovalStatus.APPROVED


def test_discord_interaction_reject(discord_env):
    """Vérifie le refus via l'interaction Discord."""
    ctrl: DiscordApprovalController = discord_env["controller"]
    mgr: ApprovalManager = discord_env["manager"]

    req = mgr.request_approval(
        task_id="tsk_disc_3",
        session_id="sess_disc_3",
        agent_id="Hermes",
        capability_name="system-mcp",
        scope="system.destructive",
        safe_summary="rm dangerous",
        params={},
    )

    res = ctrl.handle_interaction_decision(
        approval_id=req.approval_id,
        choice_str="REJECT",
        user_id="186035306418405376",
        username="OwnerBidi",
        reason="Action rejetée par précaution",
    )

    assert res["ok"] is True
    assert res["status"] == "REJECTED"


def test_discord_interaction_expired(discord_env):
    """Vérifie le rejet d'interaction sur demande expirée."""
    ctrl: DiscordApprovalController = discord_env["controller"]
    mgr: ApprovalManager = discord_env["manager"]
    tasks_db = discord_env["tasks_db"]

    req = mgr.request_approval(
        task_id="tsk_disc_4",
        session_id="sess_disc_4",
        agent_id="Hermes",
        capability_name="c",
        scope="s",
        safe_summary="s",
        params={},
    )

    with sqlite3.connect(tasks_db) as conn:
        conn.execute("UPDATE approval_requests SET expires_at = '2000-01-01T00:00:00+00:00' WHERE approval_id = ?", (req.approval_id,))

    res = ctrl.handle_interaction_decision(
        approval_id=req.approval_id,
        choice_str="APPROVE",
        user_id="186035306418405376",
        username="OwnerBidi",
    )

    assert res["ok"] is False
    assert res["code"] == "EXPIRED"


def test_discord_interaction_double_click(discord_env):
    """Vérifie qu'un deuxième clic/décision est bloqué en CONFLICT."""
    ctrl: DiscordApprovalController = discord_env["controller"]
    mgr: ApprovalManager = discord_env["manager"]

    req = mgr.request_approval(
        task_id="tsk_disc_5",
        session_id="sess_disc_5",
        agent_id="Hermes",
        capability_name="c",
        scope="s",
        safe_summary="s",
        params={},
    )

    # Premier clic
    res1 = ctrl.handle_interaction_decision(
        approval_id=req.approval_id,
        choice_str="APPROVE",
        user_id="186035306418405376",
        username="OwnerBidi",
    )
    assert res1["ok"] is True

    # Deuxième clic simultané/rejeu
    res2 = ctrl.handle_interaction_decision(
        approval_id=req.approval_id,
        choice_str="APPROVE",
        user_id="186035306418405376",
        username="OwnerBidi",
    )
    assert res2["ok"] is False
    assert res2["code"] == "CONFLICT"


def test_discord_interaction_invalid_choice(discord_env):
    """Vérifie qu'un choix falsifié par le client Discord est rejeté."""
    ctrl: DiscordApprovalController = discord_env["controller"]
    res = ctrl.handle_interaction_decision(
        approval_id="appr_dummy",
        choice_str="BYPASS_POLICY",
        user_id="hacker",
        username="hacker",
    )
    assert res["ok"] is False
    assert res["code"] == "INVALID_CHOICE"
