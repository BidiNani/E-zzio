"""
Suite de tests de validation Phase 2 : Hermes MCP Gateway & Confinement E-ZZIO.
Vérifie rigoureusement les 10 points du cahier des charges :
1. Hermes read-only action -> ALLOW
2. Hermes local code patch -> ALLOW
3. Hermes drive.write -> REQUIRE_HUMAN
4. Hermes github.push -> REQUIRE_HUMAN
5. Hermes destructive system action -> DENY
6. Unknown scope -> DENY
7. Approval -> execution
8. Rejected approval -> no execution
9. Expired approval -> no execution
10. Payload mutation -> no execution
"""
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from core.capabilities.hermes_mcp_gateway import (
    HermesMCPGateway,
    MCPToolCallRequest,
)
from core.governance.approval import (
    ApprovalExpiredError,
    ApprovalManager,
    ApprovalStatus,
    DecisionChoice,
    PayloadIntegrityViolation,
    StateTransitionError,
)
from core.governance.approval.store import SqliteApprovalStore
from core.security.audit_ledger import AuditLedger
from core.tasks import manager as task_manager_mod


@pytest.fixture
def hermes_mcp_env(tmp_path: Path, monkeypatch):
    tasks_db_path = tmp_path / "hermes_tasks.db"
    audit_db_path = tmp_path / "hermes_audit.db"

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

    gateway = HermesMCPGateway(manager=mgr)

    return {
        "gateway": gateway,
        "manager": mgr,
        "tasks_db": tasks_db_path,
        "task_manager": tm,
    }


@pytest.mark.asyncio
async def test_1_hermes_read_only_allow(hermes_mcp_env):
    """1. Vérifie qu'une lecture Hermes (ex: web-search) est autorisée en ALLOW."""
    gw: HermesMCPGateway = hermes_mcp_env["gateway"]
    with patch.object(gw.registry.web_provider, "search", new=AsyncMock(return_value={"ok": True, "results": ["data"]})):
        req = MCPToolCallRequest(
            tool_name="web-search-mcp",
            arguments={"query": "python 3.12 documentation"},
        )
        res = await gw.handle_tool_call(req)
        assert res.ok is True
        assert res.status == "ALLOW"
        assert res.result["results"] == ["data"]


@pytest.mark.asyncio
async def test_2_hermes_local_code_patch_allow(hermes_mcp_env):
    """2. Vérifie qu'un patch local de code (scope code.patch) est autorisé."""
    gw: HermesMCPGateway = hermes_mcp_env["gateway"]
    with patch.object(gw.registry.web_provider, "search", new=AsyncMock(return_value={"ok": True})):
        req = MCPToolCallRequest(
            tool_name="web-search-mcp",
            arguments={"query": "test", "scope": "code.patch"},
        )
        res = await gw.handle_tool_call(req)
        assert res.ok is True
        assert res.status == "ALLOW"


@pytest.mark.asyncio
async def test_3_hermes_drive_write_require_human(hermes_mcp_env):
    """3. Vérifie que drive.write déclenche REQUIRE_HUMAN et crée un ApprovalRequest."""
    gw: HermesMCPGateway = hermes_mcp_env["gateway"]
    req = MCPToolCallRequest(
        tool_name="google-workspace-mcp",
        arguments={"service": "drive", "operation": "upload", "filename": "budget.xlsx"},
    )
    res = await gw.handle_tool_call(req)
    assert res.ok is False
    assert res.status == "REQUIRE_HUMAN"
    assert res.approval_id is not None

    # Vérification dans le manager
    appr = hermes_mcp_env["manager"].get(res.approval_id)
    assert appr.status == ApprovalStatus.PENDING
    assert appr.scope == "drive.write"


@pytest.mark.asyncio
async def test_4_hermes_github_push_require_human(hermes_mcp_env):
    """4. Vérifie que github.push déclenche REQUIRE_HUMAN."""
    gw: HermesMCPGateway = hermes_mcp_env["gateway"]
    req = MCPToolCallRequest(
        tool_name="github-mcp",
        arguments={"operation": "push", "branch": "release"},
    )
    res = await gw.handle_tool_call(req)
    assert res.ok is False
    assert res.status == "REQUIRE_HUMAN"
    assert res.approval_id is not None


@pytest.mark.asyncio
async def test_5_hermes_destructive_system_action_deny(hermes_mcp_env):
    """5. Vérifie que toute action destructive est formellement bloquée en DENY."""
    gw: HermesMCPGateway = hermes_mcp_env["gateway"]
    req = MCPToolCallRequest(
        tool_name="web-search-mcp",
        arguments={"query": "rm -rf", "scope": "system.destructive"},
    )
    res = await gw.handle_tool_call(req)
    assert res.ok is False
    assert res.status == "DENY"
    assert "POLICY DENY" in res.reason


@pytest.mark.asyncio
async def test_6_hermes_unknown_scope_deny(hermes_mcp_env):
    """6. Vérifie qu'un scope orphelin/inconnu est rejeté par défaut (Fail-Closed)."""
    gw: HermesMCPGateway = hermes_mcp_env["gateway"]
    req = MCPToolCallRequest(
        tool_name="web-search-mcp",
        arguments={"query": "test", "scope": "unauthorized.backdoor"},
    )
    res = await gw.handle_tool_call(req)
    assert res.ok is False
    assert res.status == "DENY"


@pytest.mark.asyncio
async def test_7_hermes_approval_execution(hermes_mcp_env):
    """7. Vérifie le flux complet : REQUIRE_HUMAN -> APPROVE -> Reprise exécution."""
    gw: HermesMCPGateway = hermes_mcp_env["gateway"]
    mgr: ApprovalManager = hermes_mcp_env["manager"]

    req = MCPToolCallRequest(
        tool_name="github-mcp",
        arguments={"operation": "push", "branch": "main"},
    )
    call_res = await gw.handle_tool_call(req)
    appr_id = call_res.approval_id

    # Approbation par l'opérateur
    mgr.decide(appr_id, DecisionChoice.APPROVE, decided_by="human_lead")

    # Reprise
    exec_res = await gw.resume_approved_tool_call(appr_id)
    assert exec_res.get("ok") is True
    assert exec_res.get("pushed") is True
    assert exec_res.get("branch") == "main"


@pytest.mark.asyncio
async def test_8_hermes_rejected_approval_no_execution(hermes_mcp_env):
    """8. Vérifie qu'une approbation rejetée bloque la reprise."""
    gw: HermesMCPGateway = hermes_mcp_env["gateway"]
    mgr: ApprovalManager = hermes_mcp_env["manager"]

    req = MCPToolCallRequest(
        tool_name="google-workspace-mcp",
        arguments={"service": "drive", "operation": "upload", "filename": "secret.doc"},
    )
    call_res = await gw.handle_tool_call(req)
    appr_id = call_res.approval_id

    # Refus
    mgr.decide(appr_id, DecisionChoice.REJECT, decided_by="human_lead", reason="Interdit")

    with pytest.raises(StateTransitionError):
        await gw.resume_approved_tool_call(appr_id)


@pytest.mark.asyncio
async def test_9_hermes_expired_approval_no_execution(hermes_mcp_env):
    """9. Vérifie qu'une approbation expirée bloque la reprise."""
    gw: HermesMCPGateway = hermes_mcp_env["gateway"]
    mgr: ApprovalManager = hermes_mcp_env["manager"]
    tasks_db = hermes_mcp_env["tasks_db"]

    req = MCPToolCallRequest(
        tool_name="google-workspace-mcp",
        arguments={"service": "drive", "operation": "upload", "filename": "doc.pdf"},
    )
    call_res = await gw.handle_tool_call(req)
    appr_id = call_res.approval_id

    mgr.decide(appr_id, DecisionChoice.APPROVE, decided_by="human_lead")

    # Expirer après approbation
    with sqlite3.connect(tasks_db) as conn:
        conn.execute("UPDATE approval_requests SET expires_at = '2000-01-01T00:00:00+00:00' WHERE approval_id = ?", (appr_id,))

    with pytest.raises(ApprovalExpiredError):
        await gw.resume_approved_tool_call(appr_id)


@pytest.mark.asyncio
async def test_10_hermes_payload_mutation_no_execution(hermes_mcp_env):
    """10. Vérifie que toute modification du payload stocké avorte l'exécution."""
    gw: HermesMCPGateway = hermes_mcp_env["gateway"]
    mgr: ApprovalManager = hermes_mcp_env["manager"]
    tasks_db = hermes_mcp_env["tasks_db"]

    req = MCPToolCallRequest(
        tool_name="google-workspace-mcp",
        arguments={"service": "drive", "operation": "upload", "filename": "clean.doc"},
    )
    call_res = await gw.handle_tool_call(req)
    appr_id = call_res.approval_id

    mgr.decide(appr_id, DecisionChoice.APPROVE, decided_by="human_lead")

    # Corruption du payload
    with sqlite3.connect(tasks_db) as conn:
        conn.execute("UPDATE approval_requests SET params_payload = '{\"filename\":\"malicious.exe\"}' WHERE approval_id = ?", (appr_id,))

    with pytest.raises(PayloadIntegrityViolation):
        await gw.resume_approved_tool_call(appr_id)
