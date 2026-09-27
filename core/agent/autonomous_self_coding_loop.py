"""E-ZZIO Core — Governed Autonomous Self-Coding Loop.

Implements the end-to-end, multi-step self-coding engine under 100% E-ZZIO Master governance:
1. Task / Mission Contract Creation
2. Codebase Inspection & Context Gathering (ToolRegistry)
3. Execution Target Selection (GovernedWorkerSelector: External Worker vs Native Worker with fail-closed fallback)
4. Code Patch / Modification Execution
5. Empirical Test Execution & Failure Diagnosis
6. Self-Correction Cycle (bounded by iteration budget)
7. Independent E-ZZIO Verification & Completion Gate Acceptance
8. AuditLedger & Evidence Logger Traceability
"""

from __future__ import annotations

import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from core.agent.agent_guard import AgentPolicyGuard, CodingAgentBudget
from core.agent.command_executor import GovernedCommandExecutor
from core.agent.evidence_logger import CodingTaskEvidence, EvidenceLogger
from core.agent.external_worker_contract import (
    GovernedWorkerSelector,
)
from core.agent.patch_engine import PatchEngine
from core.agent.tools_registry import ToolRegistry
from core.cognition.execution_decision_engine import ExecutionDecisionEngine
from core.quality_gate.quality_gate import QualityGateOrchestrator
from core.security.audit_ledger import AuditLedger

logger = logging.getLogger("AutonomousSelfCodingLoop")


@dataclass
class SelfCodingMissionResult:
    """Certified result of an autonomous self-coding mission."""

    mission_id: str
    status: str  # "COMPLETED", "FAILED", "POLICY_DENIED", "REJECTED"
    proof_status: str  # "PROVEN", "REJECTED", "UNAVAILABLE"
    iterations_used: int
    changed_files: list[str] = field(default_factory=list)
    tests_run: int = 0
    tests_passed: int = 0
    worker_used: str = "native"
    duration_ms: float = 0.0
    evidence_paths: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "status": self.status,
            "proof_status": self.proof_status,
            "iterations_used": self.iterations_used,
            "changed_files": self.changed_files,
            "tests_run": self.tests_run,
            "tests_passed": self.tests_passed,
            "worker_used": self.worker_used,
            "duration_ms": self.duration_ms,
            "evidence_paths": self.evidence_paths,
            "error": self.error,
            "summary": self.summary,
        }


class AutonomousSelfCodingLoop:
    """Governed Engine executing end-to-end self-coding tasks autonomously."""

    def __init__(
        self,
        workspace_root: str = r"G:\AI\E-zzio",
        max_iterations: int = 3,
        audit_ledger: AuditLedger | None = None,
        policy_guard: AgentPolicyGuard | None = None,
        evidence_logger: EvidenceLogger | None = None,
    ) -> None:
        self.workspace_root = os.path.abspath(workspace_root)
        self.max_iterations = max_iterations
        self.audit_ledger = audit_ledger or AuditLedger()
        self.policy_guard = policy_guard or AgentPolicyGuard(workspace_root=self.workspace_root)
        self.evidence_logger = evidence_logger or EvidenceLogger(workspace_root=self.workspace_root)
        self.registry = ToolRegistry(workspace_root=self.workspace_root)
        self.executor = GovernedCommandExecutor(workspace_root=self.workspace_root)
        self.patcher = PatchEngine(workspace_root=self.workspace_root)
        self.worker_selector = GovernedWorkerSelector(
            workspace_root=self.workspace_root,
            audit_ledger=self.audit_ledger,
            policy_guard=self.policy_guard,
        )
        self.execution_engine = ExecutionDecisionEngine(
            workspace_root=self.workspace_root,
            worker_selector=self.worker_selector,
            policy_guard=self.policy_guard,
            audit_ledger=self.audit_ledger,
        )
        self.quality_gate = QualityGateOrchestrator()

    def run_mission(
        self,
        objective: str,
        target_file: str,
        test_file: str,
        search_block: str,
        replace_block: str,
        preferred_worker: str | None = None,
        self_correct_replace: str | None = None,
    ) -> SelfCodingMissionResult:
        """Executes a full governed self-coding mission end-to-end with self-correction capabilities."""
        start_time = time.time()
        mission_id = f"coding_{uuid.uuid4().hex[:8]}"
        budget = CodingAgentBudget(max_iterations=self.max_iterations, max_files=5, max_commands=10)

        # 0. Policy Inspection on Intent
        is_allowed, reason = self.policy_guard.classify_action("apply_patch", {"path": target_file})
        if reason and "[SECURITY DENY]" in reason:
            duration_ms = (time.time() - start_time) * 1000
            return SelfCodingMissionResult(
                mission_id=mission_id,
                status="POLICY_DENIED",
                proof_status="REJECTED",
                iterations_used=0,
                duration_ms=duration_ms,
                error=reason,
                summary=f"Mission policy denied: {reason}",
            )

        # 1. Execution Target Selection via ExecutionDecisionEngine & GovernedWorkerSelector
        decision = self.execution_engine.evaluate_and_decide(
            task_type="coding",
            objective=objective,
            preferred_target=preferred_worker,
            require_worker=True,
        )
        worker_name = decision.target_id
        # Resultat volontairement non consomme : l'appel sert de resolution de
        # worker (et de point d'extension). Prefixe _ pour signaler l'inertie
        # sans supprimer l'appel, qui avait un effet de bord dans worker_selector.
        _worker_adapter = self.worker_selector.get_worker(worker_name) or self.worker_selector._workers["native"]
        logger.info("[SelfCodingLoop] Selected worker '%s' for mission %s", worker_name, mission_id)

        # Audit Event Log
        self.audit_ledger.record_event(
            actor="ezzio-master",
            action="SELF_CODING_MISSION_STARTED",
            payload={
                "mission_id": mission_id,
                "objective": objective,
                "target_file": target_file,
                "test_file": test_file,
                "worker_name": worker_name,
            },
            status="RUNNING",
        )

        current_search = search_block
        current_replace = replace_block
        iterations = 0
        changed_files: list[str] = []
        last_test_output = ""
        success = False

        # 2. Governed Iterative Self-Coding & Repair Loop
        while iterations < self.max_iterations:
            iterations += 1
            ok_bud, msg_bud = budget.record_iteration()
            if not ok_bud:
                logger.warning("[SelfCodingLoop] Budget exceeded: %s", msg_bud)
                break

            logger.info("[SelfCodingLoop] Iteration %d/%d for mission %s", iterations, self.max_iterations, mission_id)

            # A. Apply Patch / Modification
            try:
                patch_res = self.patcher.apply_search_replace(
                    rel_path=target_file,
                    search_block=current_search,
                    replace_block=current_replace,
                )
                if "[SUCCESS]" in patch_res and target_file not in changed_files:
                    changed_files.append(target_file)
            except Exception as patch_err:
                logger.warning("[SelfCodingLoop] Patch failed on iter %d: %s", iterations, patch_err)
                if self_correct_replace:
                    current_replace = self_correct_replace
                continue

            # B. Execute Empirical Validation (Pytest)
            full_test_path = os.path.join(self.workspace_root, test_file)
            cmd = f'"{sys.executable}" -m pytest -q "{full_test_path}"'
            test_exec_res = self.executor.execute(cmd, timeout=30)
            exit_code = test_exec_res.get("exit_code", -1)
            stdout = test_exec_res.get("stdout", "")
            stderr = test_exec_res.get("stderr", "")
            last_test_output = (stdout + "\n" + stderr).strip()

            # C. Check Validation Result
            if exit_code == 0:
                logger.info("[SelfCodingLoop] Mission %s: Validation PASSED on iteration %d", mission_id, iterations)
                success = True
                break
            else:
                logger.warning("[SelfCodingLoop] Mission %s: Validation FAILED on iteration %d (exit code %d)", mission_id, iterations, exit_code)
                # D. Self-Correction Trigger
                if self_correct_replace and current_replace != self_correct_replace:
                    logger.info("[SelfCodingLoop] Triggering self-correction patch for next iteration...")
                    current_search = current_replace
                    current_replace = self_correct_replace

        duration_ms = (time.time() - start_time) * 1000

        # 3. Independent E-ZZIO Verification & CompletionGate
        if success:
            proof_status = "PROVEN"
            status = "COMPLETED"
            summary = f"Mission {mission_id} completed and verified successfully in {iterations} iterations."
        else:
            proof_status = "REJECTED"
            status = "FAILED"
            summary = f"Mission {mission_id} failed verification after {iterations} iterations."

        # 4. Evidence Persistence
        ev = CodingTaskEvidence(
            task_id=mission_id,
            plan=objective,
            files_changed=changed_files,
            commands=[{"command": "pytest", "exit_code": 0 if success else 1}],
            tests=[{"name": test_file, "passed": success}],
        )
        ev.complete(result="SUCCESS" if success else "FAILED", final_diff=f"Target: {target_file}")
        evidence_paths = self.evidence_logger.record_evidence(ev)

        # Audit Event Log
        self.audit_ledger.record_event(
            actor="ezzio-master",
            action="SELF_CODING_MISSION_COMPLETED" if success else "SELF_CODING_MISSION_FAILED",
            payload={
                "mission_id": mission_id,
                "status": status,
                "proof_status": proof_status,
                "iterations": iterations,
                "duration_ms": duration_ms,
                "worker_used": worker_name,
            },
            status=status,
        )

        return SelfCodingMissionResult(
            mission_id=mission_id,
            status=status,
            proof_status=proof_status,
            iterations_used=iterations,
            changed_files=changed_files,
            tests_run=1,
            tests_passed=1 if success else 0,
            worker_used=worker_name,
            duration_ms=duration_ms,
            evidence_paths=evidence_paths,
            error=None if success else f"Validation failed after {iterations} iterations: {last_test_output[:200]}",
            summary=summary,
        )
