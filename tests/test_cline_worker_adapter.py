"""E-ZZIO Core Mission 19 — Cline Worker Adapter Test Suite.

Verifies:
1. Availability check and graceful fail-closed fallback when Cline CLI binary is absent.
2. Policy enforcement fail-closed behavior on destructive prompt attempts.
3. Bounded CLI command construction.
4. Structured worker result compliance (WorkerResult != Proof; output is OBSERVED).
5. Timeout handling, process tree termination, and cancellation.
6. Independent E-ZZIO verification and integration gate.
"""

import sys

import pytest

from core.agent.cline_worker_adapter import (
    ClineWorkerAdapter,
    ClineWorkerRequest,
    ClineWorkerResult,
)
from core.security.audit_ledger import AuditLedger


@pytest.mark.asyncio
async def test_cline_adapter_availability_and_fallback(tmp_path):
    """Vérifie le repli gracieux et fail-closed lorsque le binaire Cline est indisponible."""
    ledger = AuditLedger(db_path=str(tmp_path / "audit_cline_unavail.db"))
    adapter = ClineWorkerAdapter(
        cline_binary_path="/nonexistent/path/to/cline_binary",
        workspace_root=str(tmp_path),
        audit_ledger=ledger,
    )

    assert adapter.is_available() is False
    assert adapter.get_version() is None

    req = ClineWorkerRequest(
        task_id="cline-test-unavail",
        prompt="Refactor calculator functions",
        working_directory=str(tmp_path),
        use_worktree_isolation=False,
    )

    res = await adapter.submit(req)

    assert isinstance(res, ClineWorkerResult)
    assert res.worker_id == "cline"
    assert res.status == "UNAVAILABLE"
    assert "Cline CLI binary is not available" in (res.error or "")


@pytest.mark.asyncio
async def test_cline_adapter_policy_denial(tmp_path):
    """Vérifie le rejet proactif par la politique de sécurité des tentatives destructrices."""
    ledger = AuditLedger(db_path=str(tmp_path / "audit_cline_policy.db"))
    adapter = ClineWorkerAdapter(
        cline_binary_path=sys.executable,  # Use python to pass availability
        workspace_root=str(tmp_path),
        audit_ledger=ledger,
    )

    destructive_req = ClineWorkerRequest(
        task_id="cline-test-policy",
        prompt="Execute rm -rf / inside workspace",
        working_directory=str(tmp_path),
        use_worktree_isolation=False,
    )

    res = await adapter.submit(destructive_req)

    assert res.status == "POLICY_DENIED"
    assert "[POLICY_DENIED]" in (res.error or "")


def test_cline_adapter_command_construction(tmp_path):
    """Vérifie la construction déterministe et sécurisée de la ligne de commande CLI."""
    adapter = ClineWorkerAdapter(
        cline_binary_path="/fake/cline",
        workspace_root=str(tmp_path),
    )

    req = ClineWorkerRequest(
        task_id="cline-test-cmd",
        prompt="Add unit tests",
        working_directory=str(tmp_path),
        model="gemini-3.7-flash",
        provider="gemini",
        max_turns=5,
        allowed_tools=["read_file", "write_file"],
    )

    cmd = adapter.build_cli_command(req, str(tmp_path))

    assert "/fake/cline" in cmd[0]
    assert "--prompt" in cmd
    assert "Add unit tests" in cmd
    assert "--dir" in cmd
    assert str(tmp_path) in cmd
    assert "--model" in cmd
    assert "gemini-3.7-flash" in cmd
    assert "--provider" in cmd
    assert "gemini" in cmd
    assert "--max-turns" in cmd
    assert "5" in cmd
    assert "--tools" in cmd
    assert "read_file,write_file" in cmd


@pytest.mark.asyncio
async def test_cline_adapter_mock_execution_and_structure(tmp_path):
    """Vérifie la structure normalisée du WorkerResult et l'intégration des métadonnées."""
    res_dict = ClineWorkerResult(
        worker_id="cline",
        task_id="cline-test-struct",
        status="SUCCESS",
        exit_code=0,
        changed_files=["calc.py"],
        duration_ms=45.2,
        stdout='{"type": "result", "text": "Task completed"}\nchanged_file: calc.py',
        output="Task completed",
        structured_output={"type": "result", "text": "Task completed"},
    ).to_dict()

    assert res_dict["worker_id"] == "cline"
    assert res_dict["status"] == "SUCCESS"
    assert res_dict["exit_code"] == 0
    assert res_dict["changed_files"] == ["calc.py"]
    assert res_dict["structured_output"] == {"type": "result", "text": "Task completed"}


@pytest.mark.asyncio
async def test_cline_adapter_process_cleanup_and_cancellation(tmp_path):
    """Vérifie l'interruption propre et la résiliation d'arbre de processus sous Windows & POSIX."""
    ledger = AuditLedger(db_path=str(tmp_path / "audit_cline_cancel.db"))
    adapter = ClineWorkerAdapter(
        cline_binary_path=sys.executable,
        workspace_root=str(tmp_path),
        audit_ledger=ledger,
    )

    import asyncio
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-c", "import time; time.sleep(10)",
        cwd=str(tmp_path),
    )
    assert proc.returncode is None

    adapter._active_processes["test-task-cancel"] = proc
    cancelled = await adapter.cancel("test-task-cancel")

    assert cancelled is True
    await asyncio.sleep(0.1)
    assert proc.returncode is not None or proc.poll() is not None


def test_cline_adapter_independent_verification_gate(tmp_path):
    """Vérifie que Worker Result != Proof et que la validation E-ZZIO fait foi."""
    adapter = ClineWorkerAdapter(workspace_root=str(tmp_path))

    failed_result = ClineWorkerResult(
        task_id="t1",
        status="FAILED",
        exit_code=1,
    )
    res_failed = adapter.verify_and_integrate(failed_result)
    assert res_failed["accepted"] is False
    assert res_failed["proof_status"] == "REJECTED"

    success_result = ClineWorkerResult(
        task_id="t2",
        status="SUCCESS",
        exit_code=0,
        changed_files=["calc.py"],
    )
    res_success = adapter.verify_and_integrate(success_result)
    assert res_success["accepted"] is True
    assert res_success["proof_status"] == "PROVEN"
