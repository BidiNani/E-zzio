"""Tests pour SelfCodingLoopAdapter sous la gouvernance canonique E-ZZIO.

Vérifie l'encapsulation de AutonomousSelfCodingLoop dans le contrat BaseWorkerAdapter,
l'exécution sous contrôle Master, et le scellement de preuve via CompletionGate.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.agent.external_worker_contract import (
    GovernedWorkerSelector,
    WorkerRequest,
    WorkerResult,
    validate_worker_pre_execution,
)
from core.agent.self_coding_loop_adapter import SelfCodingLoopAdapter
from core.cognition.execution_decision_engine import ExecutionDecision
from core.security.audit_ledger import AuditLedger


@pytest.fixture
def adapter():
    return SelfCodingLoopAdapter(workspace_root=r"G:\AI\E-zzio")


@pytest.mark.asyncio
async def test_a_self_coding_loop_adapter_contract(adapter):
    """Test A: Verifies SelfCodingLoopAdapter adheres to BaseWorkerAdapter contract."""
    assert adapter.is_available() is True
    assert "SelfCodingLoop" in adapter.get_version()
    assert adapter.worker_id == "self_coding_loop"


@pytest.mark.asyncio
async def test_b_pre_execution_guard_blocks_unauthorized_decision(adapter):
    """Test B: Pre-execution guard rejects execution without valid ExecutionDecision."""
    req = WorkerRequest(task_id="t1", prompt="Fix bug")
    result = await adapter.submit(req, execution_decision=None)
    assert result.status == "POLICY_DENIED"
    assert result.exit_code == -2
    assert "[PRE_EXECUTION_DENIED]" in result.error


@pytest.mark.asyncio
async def test_c_pre_execution_guard_mismatch_target(adapter):
    """Test C: Pre-execution guard rejects decision targeting wrong worker."""
    decision = ExecutionDecision(
        execution_type="WORKER",
        target_id="hermes",
        provider="hermes",
        is_local=False,
        score=80.0,
        rationale="Targeted hermes",
    )
    req = WorkerRequest(task_id="t2", prompt="Fix bug")
    result = await adapter.submit(req, execution_decision=decision)
    assert result.status == "POLICY_DENIED"
    assert result.exit_code == -2
    assert "Worker target mismatch" in result.error


@pytest.mark.asyncio
async def test_d_governed_worker_selector_registers_self_coding_loop():
    """Test D: GovernedWorkerSelector registers self_coding_loop adapter."""
    selector = GovernedWorkerSelector(workspace_root=r"G:\AI\E-zzio")
    w = selector.get_worker("self_coding_loop")
    assert w is not None
    assert isinstance(w, SelfCodingLoopAdapter)

    w_alias = selector.get_worker("self_coding")
    assert w_alias is not None


@pytest.mark.asyncio
async def test_e_successful_adapter_execution(adapter):
    """Test E: Successful submission returns WorkerResult with status SUCCESS."""
    decision = ExecutionDecision(
        execution_type="WORKER",
        target_id="self_coding_loop",
        provider="native_agent",
        is_local=True,
        score=100.0,
        rationale="Self coding requested",
    )
    req = WorkerRequest(
        task_id="t3",
        prompt="Fix math function",
        context={
            "target_file": "core/agent/self_coding_loop_adapter.py",
            "test_file": "tests/test_self_coding_loop_adapter.py",
            "search_block": "# DUMMY_SEARCH",
            "replace_block": "# DUMMY_REPLACE",
        },
    )

    mock_mission_res = MagicMock()
    mock_mission_res.status = "COMPLETED"
    mock_mission_res.proof_status = "PROVEN"
    mock_mission_res.changed_files = ["core/agent/self_coding_loop_adapter.py"]
    mock_mission_res.summary = "Mission coding_123: PROVEN"
    mock_mission_res.tests_run = 1
    mock_mission_res.tests_passed = 1
    mock_mission_res.error = None

    with patch.object(adapter.loop, "run_mission", return_value=mock_mission_res):
        res = await adapter.submit(req, execution_decision=decision)
        assert res.status == "SUCCESS"
        assert res.exit_code == 0
        assert res.worker_id == "self_coding_loop"
        assert "core/agent/self_coding_loop_adapter.py" in res.changed_files


@pytest.mark.asyncio
async def test_f_verify_and_integrate_delegates_to_completion_gate(adapter):
    """Test F: verify_and_integrate delegates proof sealing to CompletionGate."""
    from core.agent.evidence_logger import CodingTaskEvidence

    w_res = WorkerResult(
        worker_id="self_coding_loop",
        worker_type="native_agent",
        task_id="t4",
        status="SUCCESS",
        exit_code=0,
    )
    ev = CodingTaskEvidence(
        task_id="t4",
        plan="Fix bug",
        files_changed=["core/agent/self_coding_loop_adapter.py"],
        commands=[{"command": "pytest", "exit_code": 0}],
        tests=[{"name": "test_self_coding_loop_adapter.py", "passed": True}],
    )
    ev.complete(result="SUCCESS", final_diff="Target: core/agent/self_coding_loop_adapter.py")

    decision = adapter.verify_and_integrate(w_res, evidence=ev)
    assert decision["accepted"] is True
    assert decision["proof_status"] == "PROVEN"
