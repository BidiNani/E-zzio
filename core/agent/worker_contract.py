"""
E-ZZIO Hierarchical Orchestration — Worker Contract Specifications (L0/L1/L2).
"""
from __future__ import annotations

import enum
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

SCHEMA_REQUEST = "ezzio.worker_task.v1"

class ContractViolationError(ValueError):
    """Exception levée en cas de violation du contrat d'agent worker."""
    pass


class ResultStatus(enum.StrEnum):
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    NEEDS_ESCALATION = "NEEDS_ESCALATION"


class ArbitrationVerdict(enum.StrEnum):
    COMPATIBLE = "COMPATIBLE"
    COMPLEMENTARY = "COMPLEMENTARY"
    CONFLICTED = "CONFLICTED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass
class Budget:
    max_tool_calls: int = 100
    timeout_sec: int = 600
    max_tokens: int = 100000

    def fits_within(self, parent: Budget) -> tuple[bool, list[str]]:
        violations = []
        if self.max_tool_calls > parent.max_tool_calls:
            violations.append(f"max_tool_calls ({self.max_tool_calls}) > parent ({parent.max_tool_calls})")
        if self.timeout_sec > parent.timeout_sec:
            violations.append(f"timeout_sec ({self.timeout_sec}) > parent ({parent.timeout_sec})")
        if self.max_tokens > parent.max_tokens:
            violations.append(f"max_tokens ({self.max_tokens}) > parent ({parent.max_tokens})")
        return len(violations) == 0, violations


_FORBIDDEN_PROMPTS = [
    "ignore policy",
    "cancel all",
    "spawn another worker",
    "reveal credentials",
    "mark verified without evidence",
    "change policy",
    "sans limite",
    "ignore previous instructions",
]

@dataclass
class WorkerTaskRequest:
    request_id: str
    task_id: str
    parent_task_id: str | None = None
    worker_id: str = "coder_worker"
    worker_type: str = "CODER_WORKER"
    objective: str = ""
    authorized_tools: tuple[str, ...] = ("read_file",)
    authorized_models: tuple[str, ...] = ("qwen2.5-coder:7b-instruct-q4_K_M",)
    budget: Budget = field(default_factory=Budget)
    priority: str = "P2"
    context: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_REQUEST
    depth: int = 0
    max_children: int = 2
    context_classes: tuple[str, ...] = ()

    def ensure_valid(self) -> None:
        try:
            uuid.UUID(self.request_id)
        except Exception:
            raise ContractViolationError(f"Invalid request_id UUID: {self.request_id}") from None

        obj = self.objective.strip()
        if not obj:
            raise ContractViolationError("Objective cannot be empty.")
        if len(obj) > 4000:
            raise ContractViolationError("Objective exceeds 4000 chars.")

        obj_lower = obj.lower()
        for forbidden in _FORBIDDEN_PROMPTS:
            if forbidden in obj_lower:
                raise ContractViolationError(f"Forbidden prompt detected in objective: {forbidden}")

        if self.priority not in ("P0", "P1", "P2"):
            raise ContractViolationError(f"Invalid priority: {self.priority}")

        if self.depth >= 3:
            raise ContractViolationError(f"Depth {self.depth} exceeds maximum allowed (2)")

        if self.depth == 2 and self.max_children > 0:
            raise ContractViolationError("Worker at max depth cannot spawn children.")

        if "SECRET" in self.context_classes:
            raise ContractViolationError("Secret context is strictly forbidden.")

        import json
        if len(json.dumps(self.context)) > 8000:
            raise ContractViolationError("Context exceeds size limit.")

        if self.budget.timeout_sec <= 0 or self.budget.max_tool_calls < 0 or self.budget.max_tokens < 0:
            raise ContractViolationError("Invalid budget parameters.")

        if self.schema_version != SCHEMA_REQUEST:
            raise ContractViolationError(f"Invalid schema version: {self.schema_version}")

    def authorize_against(
        self,
        known_workers: Sequence[str],
        known_tools: Sequence[str],
        known_models: Sequence[str],
    ) -> list[str]:
        errs = []
        if self.worker_type not in known_workers:
            errs.append(f"worker inconnu: {self.worker_type}")
        for t in self.authorized_tools:
            if t not in known_tools:
                errs.append(f"outils inconnus: {t}")
        if not self.authorized_models:
            errs.append("authorized_models vide")
        else:
            for m in self.authorized_models:
                if m not in known_models:
                    errs.append(f"modeles non qualifiés: {m}")
        return errs


@dataclass
class WorkerTaskResult:
    request_id: str
    task_id: str
    worker_id: str
    status: ResultStatus = ResultStatus.COMPLETED
    summary: str = ""
    errors: tuple[str, ...] = ()
    result_version: int = 1

    def ensure_valid(self) -> None:
        try:
            uuid.UUID(self.request_id)
        except Exception:
            raise ContractViolationError(f"Invalid request_id UUID: {self.request_id}") from None

        if self.status == ResultStatus.COMPLETED and self.errors:
            raise ContractViolationError("COMPLETED result cannot contain errors.")

    def with_update(self, **kwargs) -> WorkerTaskResult:
        data = {
            "request_id": self.request_id,
            "task_id": self.task_id,
            "worker_id": self.worker_id,
            "status": self.status,
            "summary": self.summary,
            "errors": self.errors,
            "result_version": self.result_version + 1,
        }
        data.update(kwargs)
        return WorkerTaskResult(**data)


def accept_result(result: WorkerTaskResult, request: WorkerTaskRequest, known_workers: Sequence[str]) -> tuple[bool, str]:
    if result.request_id != request.request_id:
        return False, "request_id mismatch"
    if result.worker_id != request.worker_id and result.worker_id not in known_workers:
        return False, "worker_id mismatch"
    return True, "OK"


def build_escalation(request: WorkerTaskRequest, reason: str) -> WorkerTaskResult:
    return WorkerTaskResult(
        request_id=request.request_id,
        task_id=request.task_id,
        worker_id=request.worker_id,
        status=ResultStatus.NEEDS_ESCALATION,
        summary=reason,
        errors=(reason,),
    )


def check_no_horizontal_call(caller: str, callee: str) -> None:
    horizontal_workers = {"researcher_scout", "coder_worker", "qa_worker", "security_auditor"}
    if caller in horizontal_workers and callee in horizontal_workers:
        raise ContractViolationError(f"Horizontal call from {caller} to {callee} is prohibited.")


def arbitrate_statuses(statuses: Sequence[ResultStatus]) -> ArbitrationVerdict:
    if not statuses:
        return ArbitrationVerdict.INSUFFICIENT
    set_s = set(statuses)
    if ResultStatus.NEEDS_ESCALATION in set_s:
        return ArbitrationVerdict.INSUFFICIENT
    if ResultStatus.FAILED in set_s and ResultStatus.COMPLETED in set_s:
        return ArbitrationVerdict.CONFLICTED
    if set_s == {ResultStatus.FAILED}:
        return ArbitrationVerdict.INSUFFICIENT
    if set_s == {ResultStatus.COMPLETED}:
        return ArbitrationVerdict.COMPATIBLE
    if ResultStatus.PARTIAL in set_s and ResultStatus.COMPLETED in set_s:
        return ArbitrationVerdict.COMPLEMENTARY
    return ArbitrationVerdict.INSUFFICIENT
