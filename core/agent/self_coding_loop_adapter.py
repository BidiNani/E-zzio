"""E-ZZIO Autonomous Agent — Governed SelfCodingLoop Adapter.

Connects AutonomousSelfCodingLoop to Master Governance, enforcing BaseWorkerAdapter,
pre-execution validation, canonical routing via ExecutionDecisionEngine/GovernedWorkerSelector,
and evidence-based proof sealing via CompletionGate.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from core.agent.agent_guard import AgentPolicyGuard
from core.agent.autonomous_self_coding_loop import AutonomousSelfCodingLoop
from core.agent.external_worker_contract import (
    BaseWorkerAdapter,
    WorkerRequest,
    WorkerResult,
    validate_worker_pre_execution,
)
from core.quality_gate.completion_gate import CompletionGate
from core.security.audit_ledger import AuditLedger

logger = logging.getLogger("SelfCodingLoopAdapter")


class SelfCodingLoopAdapter(BaseWorkerAdapter):
    """Governed Adapter connecting AutonomousSelfCodingLoop to Master Governance."""

    def __init__(
        self,
        workspace_root: str = r"G:\AI\E-zzio",
        audit_ledger: AuditLedger | None = None,
        policy_guard: AgentPolicyGuard | None = None,
        max_iterations: int = 3,
    ) -> None:
        self.workspace_root = os.path.abspath(workspace_root)
        self.audit_ledger = audit_ledger or AuditLedger()
        self.policy_guard = policy_guard or AgentPolicyGuard(workspace_root=self.workspace_root)
        self.max_iterations = max_iterations
        self.worker_id = "self_coding_loop"
        self.loop = AutonomousSelfCodingLoop(
            workspace_root=self.workspace_root,
            max_iterations=self.max_iterations,
            audit_ledger=self.audit_ledger,
            policy_guard=self.policy_guard,
        )

    def is_available(self) -> bool:
        return True

    def get_version(self) -> str | None:
        return "E-ZZIO AutonomousSelfCodingLoop 2.0 (Governed)"

    async def submit(
        self,
        request: WorkerRequest,
        execution_decision: Any | None = None,
    ) -> WorkerResult:
        start_time = time.time()

        # 1. Pre-execution guard check
        allowed, reason = validate_worker_pre_execution("self_coding_loop", execution_decision)
        if not allowed:
            duration_ms = (time.time() - start_time) * 1000
            return WorkerResult(
                worker_id="self_coding_loop",
                worker_type="native_agent",
                task_id=request.task_id,
                status="POLICY_DENIED",
                exit_code=-2,
                duration_ms=duration_ms,
                error=reason,
            )

        # 2. Extract parameters from request context
        target_file = request.context.get("target_file", "core/agent/autonomous_self_coding_loop.py")
        test_file = request.context.get("test_file", "tests/test_autonomous_self_coding_loop.py")
        search_block = request.context.get("search_block", "")
        replace_block = request.context.get("replace_block", "")
        self_correct_replace = request.context.get("self_correct_replace")
        preferred_worker = request.context.get("preferred_worker", "self_coding_loop")

        # 3. Policy inspection on target path
        is_ok, p_reason = self.policy_guard.classify_action("apply_patch", {"path": target_file})
        if p_reason and "[SECURITY DENY]" in p_reason:
            duration_ms = (time.time() - start_time) * 1000
            return WorkerResult(
                worker_id="self_coding_loop",
                worker_type="native_agent",
                task_id=request.task_id,
                status="POLICY_DENIED",
                exit_code=-2,
                duration_ms=duration_ms,
                error=p_reason,
            )

        # 4. Execute autonomous self-coding mission
        try:
            res = self.loop.run_mission(
                objective=request.prompt or request.objective,
                target_file=target_file,
                test_file=test_file,
                search_block=search_block,
                replace_block=replace_block,
                preferred_worker=preferred_worker,
                self_correct_replace=self_correct_replace,
            )

            duration_ms = (time.time() - start_time) * 1000
            exit_code = 0 if res.status == "COMPLETED" and res.proof_status == "PROVEN" else 1

            return WorkerResult(
                worker_id="self_coding_loop",
                worker_type="native_agent",
                task_id=request.task_id,
                status="SUCCESS" if exit_code == 0 else "FAILED",
                exit_code=exit_code,
                duration_ms=duration_ms,
                output=res.summary or ("[SelfCodingLoop] Mission completed successfully." if exit_code == 0 else res.error or "Failed"),
                changed_files=res.changed_files,
                tests_run=res.tests_run,
                tests_passed=res.tests_passed,
                error=res.error,
                provenance={"worker": "self_coding_loop", "version": self.get_version(), "proof_status": res.proof_status},
            )
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            return WorkerResult(
                worker_id="self_coding_loop",
                worker_type="native_agent",
                task_id=request.task_id,
                status="FAILED",
                exit_code=1,
                duration_ms=duration_ms,
                error=str(exc),
            )

    async def cancel(self, task_id: str) -> bool:
        return True

    def verify_and_integrate(self, result: WorkerResult, evidence: Any | None = None) -> dict[str, Any]:
        gate = CompletionGate(audit_ledger=self.audit_ledger)
        decision = gate.evaluate(
            validation_passed=(result.status == "SUCCESS" and result.exit_code == 0),
            evidence=evidence,
            worker_result=result,
            exit_code=result.exit_code,
        )
        return decision.to_dict()
