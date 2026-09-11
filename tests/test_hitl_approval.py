"""
Suite de tests unitaires et d'intégration : Human-in-the-Loop (HITL) Approval System.
Vérifie rigoureusement les 16 points obligatoires du cahier des charges :
1. création PENDING
2. création avec payload_hash
3. APPROVE
4. REJECT
5. expiration TTL
6. approbation après expiration refusée
7. resume APPROVED
8. resume REJECTED refusé
9. resume EXPIRED refusé
10. payload modifié refusé
11. task mismatch refusé
12. session mismatch refusé
13. double resume
14. concurrence / double dispatch
15. audit des événements
16. intégration approval_id avec governed_tasks
"""
import asyncio
import json
import sqlite3
import time
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from core.governance.approval import (
    ApprovalDecision,
    ApprovalExpiredError,
    ApprovalManager,
    ApprovalRequest,
    ApprovalStatus,
    ContextMismatchError,
    DecisionChoice,
    DoubleExecutionError,
    ExecutionState,
    PayloadIntegrityViolation,
    StateTransitionError,
)
from core.governance.approval.manager import canonical_json, compute_payload_hash
from core.governance.approval.store import SqliteApprovalStore
from core.security.audit_ledger import AuditLedger
from core.tasks import manager as task_manager_mod


@pytest.fixture
def hitl_env(tmp_path: Path, monkeypatch):
    """Prépare un environnement isolé avec SQLite pour tasks.db, approval_requests et audit_ledger."""
    tasks_db_path = tmp_path / "test_tasks.db"
    audit_db_path = tmp_path / "test_audit.db"

    # Initialisation table governed_tasks
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
    # Réinitialiser instance task_manager
    tm = task_manager_mod.TaskManager()
    monkeypatch.setattr(task_manager_mod, "task_manager", tm)

    store = SqliteApprovalStore(db_path=tasks_db_path)
    ledger = AuditLedger(db_path=str(audit_db_path))
    mgr = ApprovalManager(store=store, audit_ledger=ledger)

    # Créer une tâche support de test
    tm.create_task(
        task_id="tsk_test_001",
        title="Tâche de test HITL",
        workspace=r"G:\AI\E-zzio",
        scope={"mode": "write"},
        plan={"steps": ["step1"]},
    )
    tm.transition_task("tsk_test_001", "SCOPED")
    tm.transition_task("tsk_test_001", "PLANNED")

    return {
        "manager": mgr,
        "store": store,
        "ledger": ledger,
        "task_manager": tm,
        "tasks_db": tasks_db_path,
        "audit_db": audit_db_path,
    }


def test_1_creation_pending(hitl_env):
    """1. Vérifie la création d'une requête avec statut PENDING."""
    mgr: ApprovalManager = hitl_env["manager"]
    req = mgr.request_approval(
        task_id="tsk_test_001",
        session_id="sess_001",
        agent_id="coding_worker",
        capability_name="google-workspace-mcp",
        scope="drive.write",
        safe_summary="Upload file to drive",
        params={"filename": "report.pdf", "folder": "root"},
    )

    assert req.approval_id.startswith("appr_")
    assert req.status == ApprovalStatus.PENDING
    assert req.execution_state == ExecutionState.NOT_STARTED

    fetched = mgr.get(req.approval_id)
    assert fetched is not None
    assert fetched.approval_id == req.approval_id
    assert fetched.status == ApprovalStatus.PENDING


def test_2_creation_with_payload_hash(hitl_env):
    """2. Vérifie le calcul exact et canonique du SHA-256 du payload."""
    mgr: ApprovalManager = hitl_env["manager"]
    params = {"b": 2, "a": 1, "nested": {"z": 10, "y": 20}}
    expected_hash = compute_payload_hash(params)

    req = mgr.request_approval(
        task_id="tsk_test_001",
        session_id="sess_001",
        agent_id="coding_worker",
        capability_name="github-mcp",
        scope="github.push",
        safe_summary="Push to main",
        params=params,
    )

    assert req.payload_hash == expected_hash
    assert req.params_payload == canonical_json(params)


def test_3_approve(hitl_env):
    """3. Vérifie la transition PENDING -> APPROVED par décision humaine."""
    mgr: ApprovalManager = hitl_env["manager"]
    req = mgr.request_approval(
        task_id="tsk_test_001",
        session_id="sess_001",
        agent_id="coding_worker",
        capability_name="drive-mcp",
        scope="drive.write",
        safe_summary="Save drive",
        params={"id": 123},
    )

    decided = mgr.decide(
        approval_id=req.approval_id,
        choice=DecisionChoice.APPROVE,
        decided_by="operator_alice",
        reason="Action approuvée",
    )

    assert decided.status == ApprovalStatus.APPROVED
    assert decided.decided_by == "operator_alice"
    assert decided.decision_reason == "Action approuvée"
    assert decided.decided_at is not None


def test_4_reject(hitl_env):
    """4. Vérifie la transition PENDING -> REJECTED et l'annulation de la tâche."""
    mgr: ApprovalManager = hitl_env["manager"]
    tm = hitl_env["task_manager"]
    req = mgr.request_approval(
        task_id="tsk_test_001",
        session_id="sess_001",
        agent_id="coding_worker",
        capability_name="drive-mcp",
        scope="drive.delete",
        safe_summary="Purge folder",
        params={"purge": True},
    )

    decided = mgr.decide(
        approval_id=req.approval_id,
        choice=DecisionChoice.REJECT,
        decided_by="operator_bob",
        reason="Opération trop risquée",
    )

    assert decided.status == ApprovalStatus.REJECTED
    # Vérifie que la tâche a été annulée
    task = tm.get_task("tsk_test_001")
    assert task["state"] == "CANCELLED"


def test_5_expiration_ttl(hitl_env):
    """5. Vérifie qu'après expiration du TTL la demande passe en EXPIRED."""
    mgr: ApprovalManager = hitl_env["manager"]
    req = mgr.request_approval(
        task_id="tsk_test_001",
        session_id="sess_001",
        agent_id="coding_worker",
        capability_name="drive-mcp",
        scope="drive.write",
        safe_summary="Quick write",
        params={"q": 1},
        ttl_seconds=10,  # Clamped à 10s
    )

    # Simuler le passage du temps en modifiant expires_at dans la base
    with sqlite3.connect(hitl_env["tasks_db"]) as conn:
        conn.execute("UPDATE approval_requests SET expires_at = '2000-01-01T00:00:00+00:00' WHERE approval_id = ?", (req.approval_id,))

    # Récupération : doit déclencher l'auto-expiration
    fetched = mgr.get(req.approval_id)
    assert fetched.status == ApprovalStatus.EXPIRED


def test_6_approbation_apres_expiration_refusee(hitl_env):
    """6. Vérifie qu'une tentative d'approbation sur une demande expirée lève ApprovalExpiredError."""
    mgr: ApprovalManager = hitl_env["manager"]
    req = mgr.request_approval(
        task_id="tsk_test_001",
        session_id="sess_001",
        agent_id="coding_worker",
        capability_name="drive-mcp",
        scope="drive.write",
        safe_summary="Quick write",
        params={"q": 1},
    )

    # Expirer artificiellement
    with sqlite3.connect(hitl_env["tasks_db"]) as conn:
        conn.execute("UPDATE approval_requests SET expires_at = '2000-01-01T00:00:00+00:00' WHERE approval_id = ?", (req.approval_id,))

    with pytest.raises(ApprovalExpiredError):
        mgr.decide(req.approval_id, DecisionChoice.APPROVE, decided_by="alice")


@pytest.mark.asyncio
async def test_7_resume_approved(hitl_env):
    """7. Vérifie que la reprise d'une demande APPROVED exécute la fonction et passe en CONSUMED."""
    mgr: ApprovalManager = hitl_env["manager"]
    tm = hitl_env["task_manager"]

    req = mgr.request_approval(
        task_id="tsk_test_001",
        session_id="sess_001",
        agent_id="coding_worker",
        capability_name="test-cap",
        scope="test.write",
        safe_summary="Test write",
        params={"action": "mutate"},
    )

    mgr.decide(req.approval_id, DecisionChoice.APPROVE, decided_by="alice")

    target_mock = AsyncMock(return_value={"ok": True, "result": "done"})
    res = await mgr.resume_execution(req.approval_id, target_mock)

    assert res == {"ok": True, "result": "done"}
    target_mock.assert_awaited_once_with("test-cap", {"action": "mutate"})

    # Vérification état final
    updated_req = mgr.get(req.approval_id)
    assert updated_req.execution_state == ExecutionState.CONSUMED

    # Vérification transition TaskManager (AWAITING_APPROVAL -> RUNNING -> VERIFYING)
    task = tm.get_task("tsk_test_001")
    assert task["state"] == "VERIFYING"


@pytest.mark.asyncio
async def test_8_resume_rejected_refuse(hitl_env):
    """8. Vérifie que resume sur REJECTED lève StateTransitionError."""
    mgr: ApprovalManager = hitl_env["manager"]
    req = mgr.request_approval(
        task_id="tsk_test_001",
        session_id="sess_001",
        agent_id="worker",
        capability_name="c",
        scope="s",
        safe_summary="s",
        params={},
    )
    mgr.decide(req.approval_id, DecisionChoice.REJECT, decided_by="alice")

    with pytest.raises(StateTransitionError, match="Impossible de reprendre une demande REJECTED"):
        await mgr.resume_execution(req.approval_id, AsyncMock())


@pytest.mark.asyncio
async def test_9_resume_expired_refuse(hitl_env):
    """9. Vérifie que resume sur EXPIRED lève ApprovalExpiredError."""
    mgr: ApprovalManager = hitl_env["manager"]
    req = mgr.request_approval(
        task_id="tsk_test_001",
        session_id="sess_001",
        agent_id="worker",
        capability_name="c",
        scope="s",
        safe_summary="s",
        params={},
    )
    mgr.decide(req.approval_id, DecisionChoice.APPROVE, decided_by="alice")

    # Expirer après coup
    with sqlite3.connect(hitl_env["tasks_db"]) as conn:
        conn.execute("UPDATE approval_requests SET expires_at = '2000-01-01T00:00:00+00:00' WHERE approval_id = ?", (req.approval_id,))

    with pytest.raises(ApprovalExpiredError):
        await mgr.resume_execution(req.approval_id, AsyncMock())


@pytest.mark.asyncio
async def test_10_payload_modifie_refuse(hitl_env):
    """10. Vérifie que si le payload stocké a été altéré, une PayloadIntegrityViolation est levée."""
    mgr: ApprovalManager = hitl_env["manager"]
    req = mgr.request_approval(
        task_id="tsk_test_001",
        session_id="sess_001",
        agent_id="worker",
        capability_name="c",
        scope="s",
        safe_summary="s",
        params={"amount": 100},
    )
    mgr.decide(req.approval_id, DecisionChoice.APPROVE, decided_by="alice")

    # Altération sournoise en base
    with sqlite3.connect(hitl_env["tasks_db"]) as conn:
        conn.execute(
            "UPDATE approval_requests SET params_payload = '{\"amount\":999999}' WHERE approval_id = ?",
            (req.approval_id,)
        )

    with pytest.raises(PayloadIntegrityViolation):
        await mgr.resume_execution(req.approval_id, AsyncMock())


@pytest.mark.asyncio
async def test_11_task_mismatch_refuse(hitl_env):
    """11. Vérifie qu'un mismatch sur le task_id lève ContextMismatchError."""
    mgr: ApprovalManager = hitl_env["manager"]
    req = mgr.request_approval(
        task_id="tsk_test_001",
        session_id="sess_001",
        agent_id="worker",
        capability_name="c",
        scope="s",
        safe_summary="s",
        params={},
    )
    mgr.decide(req.approval_id, DecisionChoice.APPROVE, decided_by="alice")

    with pytest.raises(ContextMismatchError, match="task_id"):
        await mgr.resume_execution(
            req.approval_id,
            AsyncMock(),
            expected_context={"task_id": "tsk_WRONG"}
        )


@pytest.mark.asyncio
async def test_12_session_mismatch_refuse(hitl_env):
    """12. Vérifie qu'un mismatch sur session_id lève ContextMismatchError."""
    mgr: ApprovalManager = hitl_env["manager"]
    req = mgr.request_approval(
        task_id="tsk_test_001",
        session_id="sess_001",
        agent_id="worker",
        capability_name="c",
        scope="s",
        safe_summary="s",
        params={},
    )
    mgr.decide(req.approval_id, DecisionChoice.APPROVE, decided_by="alice")

    with pytest.raises(ContextMismatchError, match="session_id"):
        await mgr.resume_execution(
            req.approval_id,
            AsyncMock(),
            expected_context={"session_id": "sess_WRONG"}
        )


@pytest.mark.asyncio
async def test_13_double_resume_returns_cached_result(hitl_env):
    """13. Vérifie l'idempotence : un second appel à resume retourne le résultat mis en cache."""
    mgr: ApprovalManager = hitl_env["manager"]
    req = mgr.request_approval(
        task_id="tsk_test_001",
        session_id="sess_001",
        agent_id="worker",
        capability_name="c",
        scope="s",
        safe_summary="s",
        params={"key": "val"},
    )
    mgr.decide(req.approval_id, DecisionChoice.APPROVE, decided_by="alice")

    mock_func = AsyncMock(return_value={"ok": True, "executed": 1})
    res1 = await mgr.resume_execution(req.approval_id, mock_func)
    assert res1 == {"ok": True, "executed": 1}
    assert mock_func.await_count == 1

    # Second appel immédiat
    res2 = await mgr.resume_execution(req.approval_id, mock_func)
    assert res2 == {"ok": True, "executed": 1}
    # La fonction sous-jacente N'A PAS été réexécutée
    assert mock_func.await_count == 1


@pytest.mark.asyncio
async def test_14_concurrence_double_dispatch(hitl_env):
    """14. Vérifie que sous deux appels concurrents simultanés, 1 seul gagne l'exécution."""
    mgr: ApprovalManager = hitl_env["manager"]
    req = mgr.request_approval(
        task_id="tsk_test_001",
        session_id="sess_001",
        agent_id="worker",
        capability_name="c",
        scope="s",
        safe_summary="s",
        params={},
    )
    mgr.decide(req.approval_id, DecisionChoice.APPROVE, decided_by="alice")

    exec_counter = 0

    async def slow_executor(cap, p):
        nonlocal exec_counter
        exec_counter += 1
        await asyncio.sleep(0.1)
        return {"ok": True, "counter": exec_counter}

    # Deux appels concurrents
    results = await asyncio.gather(
        mgr.resume_execution(req.approval_id, slow_executor),
        mgr.resume_execution(req.approval_id, slow_executor),
        return_exceptions=True,
    )

    # 1 appel a exécuté le slow_executor, l'autre soit a obtenu DoubleExecutionError (si en cours) soit le résultat
    assert exec_counter == 1
    # Aucun double dispatch destructif
    has_success = any(isinstance(r, dict) and r.get("ok") is True for r in results)
    assert has_success is True


def test_15_audit_des_evenements(hitl_env):
    """15. Vérifie que les événements critiques sont inscrits dans l'AuditLedger."""
    mgr: ApprovalManager = hitl_env["manager"]
    ledger: AuditLedger = hitl_env["ledger"]

    req = mgr.request_approval(
        task_id="tsk_test_001",
        session_id="sess_001",
        agent_id="worker",
        capability_name="c",
        scope="s",
        safe_summary="s",
        params={"safe": "val"},
    )

    mgr.decide(req.approval_id, DecisionChoice.APPROVE, decided_by="alice", reason="Validé")

    # Lecture des événements d'audit
    with sqlite3.connect(hitl_env["audit_db"]) as conn:
        rows = conn.execute("SELECT actor, action, status, payload_json FROM audit_trail ORDER BY id ASC").fetchall()

    actions = [r[1] for r in rows]
    assert "APPROVAL_REQUESTED" in actions
    assert "APPROVAL_APPROVED" in actions


def test_16_integration_approval_id_avec_governed_tasks(hitl_env):
    """16. Vérifie la liaison bidirectionnelle avec governed_tasks (AWAITING_APPROVAL et approval_id)."""
    mgr: ApprovalManager = hitl_env["manager"]
    tm = hitl_env["task_manager"]

    # Initialement en PLANNED
    initial_task = tm.get_task("tsk_test_001")
    assert initial_task["state"] == "PLANNED"

    req = mgr.request_approval(
        task_id="tsk_test_001",
        session_id="sess_001",
        agent_id="worker",
        capability_name="c",
        scope="s",
        safe_summary="s",
        params={},
    )

    # Vérifie que la tâche est passée en AWAITING_APPROVAL avec l'approval_id
    updated_task = tm.get_task("tsk_test_001")
    assert updated_task["state"] == "AWAITING_APPROVAL"
    assert updated_task["approval_id"] == req.approval_id
