"""E-ZZIO Autonomous Agent — Governed CoderWorker Adapter.

Connects CoderWorker to Master Governance, enforcing BaseWorkerAdapter,
pre-execution validation, canonical routing via ModelRouter/ProviderFactory,
and evidence-based proof sealing via CompletionGate.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from core.agent.agent_guard import AgentPolicyGuard
from core.agent.external_worker_contract import (
    BaseWorkerAdapter,
    WorkerRequest,
    WorkerResult,
    validate_worker_pre_execution,
)
from core.coding.coder_worker import CoderWorker
from core.coding.protocol import CodingRequest, ExecutionMode
from core.config.paths import get_project_root_str
from core.quality_gate.completion_gate import CompletionGate
from core.security.audit_ledger import AuditLedger

logger = logging.getLogger("CoderWorkerAdapter")


class CoderWorkerAdapter(BaseWorkerAdapter):
    """Governed Adapter connecting CoderWorker to Master Governance."""

    def __init__(
        self,
        workspace_root: str | None = None,
        audit_ledger: AuditLedger | None = None,
        policy_guard: AgentPolicyGuard | None = None,
    ) -> None:
        self.workspace_root = os.path.abspath(workspace_root or get_project_root_str())
        self.audit_ledger = audit_ledger or AuditLedger()
        self.policy_guard = policy_guard or AgentPolicyGuard(workspace_root=self.workspace_root)
        self.worker_id = "coder_worker"

    def is_available(self) -> bool:
        return True

    def get_version(self) -> str | None:
        return "E-ZZIO CoderWorker 2.0 (Governed)"

    async def submit(
        self,
        request: WorkerRequest,
        execution_decision: Any | None = None,
    ) -> WorkerResult:
        start_time = time.time()

        # 1. Pre-execution guard check
        allowed, reason = validate_worker_pre_execution("coder_worker", execution_decision)
        if not allowed:
            duration_ms = (time.time() - start_time) * 1000
            return WorkerResult(
                worker_id="coder_worker",
                worker_type="native_agent",
                task_id=request.task_id,
                status="POLICY_DENIED",
                exit_code=-2,
                duration_ms=duration_ms,
                error=reason,
            )

        # 2. Policy inspection on target path
        target_path = request.context.get("target_file", "core/coding/coder_worker.py")
        is_ok, p_reason = self.policy_guard.classify_action("apply_patch", {"path": target_path})
        if p_reason and "[SECURITY DENY]" in p_reason:
            duration_ms = (time.time() - start_time) * 1000
            return WorkerResult(
                worker_id="coder_worker",
                worker_type="native_agent",
                task_id=request.task_id,
                status="POLICY_DENIED",
                exit_code=-2,
                duration_ms=duration_ms,
                error=p_reason,
            )

        # 3. Instantiate underlying CoderWorker (voir bloc gouverne ci-dessous)
        is_dry_run = bool(request.context.get("dry_run"))

        # [CORRECTIF AUDIT] `ExecutionMode.AUTOMATIC` n'existe pas : l'enumeration
        # ne definit que READ_ONLY_SANDBOX, ACCEPT_EDITS et DRY_RUN, et
        # CodingPolicy.DEFAULT_ALLOWED_MODES n'autorise que les deux modes surs.
        # Toute execution hors dry_run levait donc une AttributeError (capturee en
        # "FAILED") au lieu de s'executer.
        requested_mode = ExecutionMode.DRY_RUN if is_dry_run else ExecutionMode.ACCEPT_EDITS

        # La policy de CoderWorker n'autorise par defaut que READ_ONLY_SANDBOX et
        # DRY_RUN : un mode accepte ici serait refuse plus bas, produisant un echec
        # trompeur ("Policy violation"). Le mode est donc autorise explicitement,
        # et uniquement apres les controles de gouvernance ci-dessus.
        coder = CoderWorker(
            root_dir=self.workspace_root,
            dry_run=is_dry_run,
            allowed_modes=frozenset({ExecutionMode.DRY_RUN, ExecutionMode.ACCEPT_EDITS}),
        )
        if "injected_llm_callback" in request.context:
            coder._injected_llm_callback = request.context["injected_llm_callback"]

        coder_req = CodingRequest(
            task_description=request.prompt or request.objective,
            mode=requested_mode,
            files_context=request.context.get("files_context", []),
        )


        # 4. Execute coding loop under governance
        try:
            resp = coder.execute_governed(coder_req)
            duration_ms = (time.time() - start_time) * 1000
            status = "SUCCESS" if resp.success else "FAILED"
            files_written = resp.result.get("files_written", []) if resp.result else []
            msg = str(resp.result.get("message") or resp.result.get("explanation") or (f"[CoderWorker] Tâche terminée avec succès ({len(files_written)} fichier(s) modifié(s))." if resp.success else resp.error or "Échec de CoderWorker"))

            return WorkerResult(
                worker_id="coder_worker",
                worker_type="native_agent",
                task_id=request.task_id,
                status=status,
                exit_code=0 if resp.success else 1,
                duration_ms=duration_ms,
                output=msg,
                changed_files=files_written,
                error=resp.error if not resp.success else None,
                provenance={"worker": "coder_worker", "version": self.get_version()},
            )
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            return WorkerResult(
                worker_id="coder_worker",
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
