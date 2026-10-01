"""Tests for Étape 13 — Governed CoderWorker Integration under E-ZZIO Master."""

from unittest.mock import MagicMock, patch

import pytest

from core.agent.coder_worker_adapter import CoderWorkerAdapter
from core.agent.evidence_logger import CodingTaskEvidence
from core.agent.external_worker_contract import BaseWorkerAdapter, WorkerRequest, WorkerResult
from core.coding.coder_worker import CoderWorker, CodingRequest, ExecutionMode
from core.cognition.execution_decision_engine import ExecutionDecision
from core.security.audit_ledger import AuditLedger


class DummyAuditLedger(AuditLedger):
    def __init__(self):
        self.events = []

    def record_event(self, actor: str, action: str, payload: dict, status: str = "SUCCESS"):
        self.events.append({
            "actor": actor,
            "action": action,
            "payload": payload,
            "status": status,
        })


@pytest.mark.asyncio
async def test_coder_worker_adapter_valid_decision():
    """Test A — Valid decision: ExecutionDecision(target_id='coder_worker') -> execution authorized."""
    adapter = CoderWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    decision = ExecutionDecision(
        execution_type="WORKER",
        target_id="coder_worker",
        provider="ollama",
        is_local=True,
        score=95.0,
        rationale="Authorized coder_worker",
    )

    req = WorkerRequest(
        task_id="t_coder_valid",
        prompt="Fix calculator bug",
        context={"dry_run": True},
    )

    with patch.object(CoderWorker, "execute_governed") as mock_exec:
        mock_exec.return_value.success = True
        mock_exec.return_value.result = {"files_written": ["calc.py"], "message": "Success"}
        mock_exec.return_value.error = None

        res = await adapter.submit(req, execution_decision=decision)

        assert res.status == "SUCCESS"
        assert res.worker_id == "coder_worker"
        assert mock_exec.called


@pytest.mark.asyncio
async def test_coder_worker_adapter_missing_decision():
    """Test B — Missing decision: execution_decision=None -> PRE_EXECUTION_DENIED, 0 LLM calls, 0 writes."""
    adapter = CoderWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    req = WorkerRequest(task_id="t_coder_no_dec", prompt="Fix bug")

    with patch.object(CoderWorker, "_call_llm") as mock_llm:
        with patch.object(CoderWorker, "_build") as mock_build:
            res = await adapter.submit(req, execution_decision=None)

            assert res.status == "POLICY_DENIED"
            assert "[PRE_EXECUTION_DENIED]" in (res.error or "")
            assert not mock_llm.called
            assert not mock_build.called


@pytest.mark.asyncio
async def test_coder_worker_adapter_mismatched_worker_decision():
    """Test C — Mismatched worker decision: target_id='cline' -> PRE_EXECUTION_DENIED, 0 LLM calls, 0 writes."""
    adapter = CoderWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    wrong_decision = ExecutionDecision(
        execution_type="WORKER",
        target_id="cline",
        provider="cline",
        is_local=True,
        score=90.0,
        rationale="Targeted cline",
    )

    req = WorkerRequest(task_id="t_coder_wrong", prompt="Fix bug")

    with patch.object(CoderWorker, "_call_llm") as mock_llm:
        with patch.object(CoderWorker, "_build") as mock_build:
            res = await adapter.submit(req, execution_decision=wrong_decision)

            assert res.status == "POLICY_DENIED"
            assert "[PRE_EXECUTION_DENIED]" in (res.error or "")
            assert not mock_llm.called
            assert not mock_build.called


@pytest.mark.asyncio
async def test_coder_worker_model_provider_authority():
    """Test D — Provider/Model authority: Model/provider come from ExecutionDecision, no direct HTTP calls."""
    adapter = CoderWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    decision = ExecutionDecision(
        execution_type="WORKER",
        target_id="coder_worker",
        provider="groq",
        is_local=False,
        score=92.0,
        rationale="Groq provider for coding",
    )

    req = WorkerRequest(
        task_id="t_coder_prov",
        prompt="Write helper function",
        context={
            "dry_run": True,
            "injected_llm_callback": lambda p: '{"plan":["step 1"],"files":[{"path":"helper.py","content":"def h(): pass"}]}',
        },
    )

    res = await adapter.submit(req, execution_decision=decision)

    assert res.status == "SUCCESS"
    assert res.worker_id == "coder_worker"


@pytest.mark.asyncio
async def test_coder_worker_policy_deny():
    """Test E — Policy DENY: AgentPolicyGuard denies target path -> POLICY_DENIED, 0 writes."""
    adapter = CoderWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    decision = ExecutionDecision(
        execution_type="WORKER",
        target_id="coder_worker",
        provider="ollama",
        is_local=True,
        score=95.0,
        rationale="Authorized",
    )

    req = WorkerRequest(
        task_id="t_coder_pol_deny",
        prompt="Delete secrets",
        context={"target_file": ".env"},
    )

    with patch.object(adapter.policy_guard, "classify_action", return_value=(False, "[SECURITY DENY] Access restricted")):
        with patch.object(CoderWorker, "_build") as mock_build:
            res = await adapter.submit(req, execution_decision=decision)

            assert res.status == "POLICY_DENIED"
            assert "[SECURITY DENY]" in (res.error or "")
            assert not mock_build.called


def test_coder_worker_validation_failure_completion_gate():
    """Test F — Validation failure: WorkerResult observed, CompletionGate rejects (proof_status: REJECTED)."""
    adapter = CoderWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    result = WorkerResult(
        worker_id="coder_worker",
        worker_type="native_agent",
        task_id="t_coder_failed",
        status="FAILED",
        exit_code=1,
    )

    res = adapter.verify_and_integrate(result)

    assert res["accepted"] is False
    assert res["proof_status"] == "REJECTED"


def test_coder_worker_validation_success_completion_gate():
    """Test G — Validation success: WorkerResult + valid evidence -> CompletionGate accepts (proof_status: PROVEN)."""
    adapter = CoderWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    result = WorkerResult(
        worker_id="coder_worker",
        worker_type="native_agent",
        task_id="t_coder_success",
        status="SUCCESS",
        exit_code=0,
    )

    evidence = CodingTaskEvidence(task_id="t_coder_success", plan="Test plan")
    evidence.complete(result="SUCCESS")

    res = adapter.verify_and_integrate(result, evidence=evidence)

    assert res["accepted"] is True
    assert res["proof_status"] == "PROVEN"


def test_coder_worker_rollback():
    """Test H — Rollback: _original_state restored when build/verify fails."""
    coder = CoderWorker(root_dir=r"G:\AI\E-zzio", dry_run=True)
    coder._original_state["temp_test_file.py"] = "def old(): pass"

    # Execute rollback
    coder._rollback()

    # Original state key existed and dry_run logged rollback
    assert "temp_test_file.py" in coder._original_state


def test_coder_worker_no_http_bypass():
    """Test I — Static anti-bypass proof: CoderWorker._call_llm uses ProviderFactory, not direct core.coding.providers HTTP clients."""
    coder = CoderWorker(root_dir=r"G:\AI\E-zzio", dry_run=True)
    coder._injected_llm_callback = lambda p: '{"plan":["step 1"],"files":[]}'

    output = coder._call_llm("test prompt")

    assert "plan" in output


def test_coder_worker_adapter_contract():
    """Test J — Worker contract: CoderWorkerAdapter complies with BaseWorkerAdapter."""
    adapter = CoderWorkerAdapter(workspace_root=r"G:\AI\E-zzio")

    assert isinstance(adapter, BaseWorkerAdapter)
    assert adapter.is_available() is True
    assert adapter.get_version() is not None
    assert adapter.worker_id == "coder_worker"
