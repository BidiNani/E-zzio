"""Tests for E-ZZIO Step 7 — Real Worker Governance (Hermes / Cline / PiG Pre-Execution Guard)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.agent.cline_worker_adapter import ClineWorkerAdapter, ClineWorkerRequest
from core.agent.external_worker_contract import WorkerResult
from core.agent.hermes_worker_adapter import HermesWorkerAdapter
from core.agent.pig_worker_adapter import PiGWorkerAdapter
from core.cognition.execution_decision_engine import ExecutionDecision


@pytest.mark.asyncio
async def test_hermes_without_decision():
    """Test A — Hermes sans décision: decision = None -> submit() DENY -> subprocess = 0."""
    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        res = await adapter.submit(
            task_id="t1",
            prompt="do something",
            execution_decision=None,
        )
        assert res.status == "POLICY_DENIED"
        assert "[PRE_EXECUTION_DENIED]" in (res.error or res.stderr)
        assert not mock_exec.called


@pytest.mark.asyncio
async def test_cline_without_decision():
    """Test B — Cline sans décision: decision = None -> submit() DENY -> subprocess = 0."""
    adapter = ClineWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    req = ClineWorkerRequest(task_id="t2", prompt="do something")
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        res = await adapter.submit(
            request=req,
            execution_decision=None,
        )
        assert res.status == "POLICY_DENIED"
        assert "[PRE_EXECUTION_DENIED]" in (res.error or res.stderr)
        assert not mock_exec.called


@pytest.mark.asyncio
async def test_pig_without_decision():
    """Test C — PiG sans décision: decision = None -> submit() DENY -> subprocess = 0."""
    adapter = PiGWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        res = await adapter.submit(
            task_id="t3",
            prompt="do something",
            execution_decision=None,
        )
        assert res.status in ("POLICY_DENIED", "FAILED")
        assert "[PRE_EXECUTION_DENIED]" in (res.error or "")
        assert not mock_exec.called


@pytest.mark.asyncio
async def test_mismatched_worker_id():
    """Test D — mauvais worker_id: decision.target_id != adapter.worker_id -> DENY -> subprocess = 0."""
    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    wrong_decision = ExecutionDecision(
        execution_type="WORKER",
        target_id="cline",
        provider="cline",
        is_local=True,
        score=90.0,
        rationale="Targeted cline",
    )
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        res = await adapter.submit(
            task_id="t4",
            prompt="do something",
            execution_decision=wrong_decision,
        )
        assert res.status == "POLICY_DENIED"
        assert "[PRE_EXECUTION_DENIED]" in (res.error or res.stderr)
        assert not mock_exec.called


@pytest.mark.asyncio
async def test_valid_worker_decision():
    """Test E — décision WORKER valide: WORKER decision valide -> adapter autorisé -> subprocess/mock appelé."""
    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    valid_decision = ExecutionDecision(
        execution_type="WORKER",
        target_id="hermes",
        provider="hermes",
        is_local=True,
        score=95.0,
        rationale="Hermes worker authorized",
    )
    mock_proc = AsyncMock()
    mock_proc.pid = 1234
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b'{"type":"result","text":"Output"}', b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        res = await adapter.submit(
            task_id="t5",
            prompt="do something",
            execution_decision=valid_decision,
        )
        assert mock_exec.called
        assert res.status == "SUCCESS"


@pytest.mark.asyncio
async def test_worker_result_is_not_proof():
    """Test F — WorkerResult: Démontrer WorkerResult != Evidence != PROVEN."""
    res = WorkerResult(
        worker_id="cline",
        worker_type="external_cli",
        task_id="t6",
        status="SUCCESS",
        output="Files modified successfully",
    )
    # Verification gate
    res_dict = res.to_dict()
    assert res_dict["status"] == "SUCCESS"
    assert "proof_status" not in res_dict  # Raw WorkerResult does not self-declare proof
    assert res_dict["output"] == "Files modified successfully"


@pytest.mark.asyncio
async def test_pig_local_policy_guard_denial():
    """Test G — policy locale PiG: Une violation du guard local bloque le subprocess."""
    adapter = PiGWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    valid_decision = ExecutionDecision(
        execution_type="WORKER",
        target_id="pig",
        provider="pig",
        is_local=True,
        score=90.0,
        rationale="PiG authorized",
    )
    with patch.object(adapter, "is_available", return_value=True):
        with patch.object(adapter.policy_guard, "evaluate_intent", return_value=(False, "Restricted path")):
            with patch("asyncio.create_subprocess_exec") as mock_exec:
                res = await adapter.submit(
                    task_id="t7",
                    prompt="do something",
                    execution_decision=valid_decision,
                )
                assert res.status == "FAILED"
                assert "[POLICY_DENIED]" in (res.error or "")
                assert not mock_exec.called


def test_native_worker_verify_and_integrate_requires_completion_gate():
    """Test H — NativeWorkerAdapter.verify_and_integrate() delegates to CompletionGate and requires evidence."""
    from core.agent.evidence_logger import CodingTaskEvidence
    from core.agent.external_worker_contract import NativeWorkerAdapter

    adapter = NativeWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    result = WorkerResult(worker_id="native", worker_type="native_agent", task_id="t8", status="SUCCESS", exit_code=0)

    # Without evidence -> REJECTED by CompletionGate
    res_no_ev = adapter.verify_and_integrate(result)
    assert res_no_ev["accepted"] is False
    assert res_no_ev["proof_status"] == "REJECTED"

    # With evidence -> PROVEN by CompletionGate
    ev = CodingTaskEvidence(task_id="t8", plan="Test")
    ev.complete(result="SUCCESS")
    res_ev = adapter.verify_and_integrate(result, evidence=ev)
    assert res_ev["accepted"] is True
    assert res_ev["proof_status"] == "PROVEN"
