"""
E-ZZIO Sovereign Governance — HITL Approval Models.
Définit les structures contractuelles immuables et typées pour l'arbitrage humain.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class ExecutionState(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    RUNNING = "RUNNING"
    CONSUMED = "CONSUMED"
    FAILED_DURING_EXECUTION = "FAILED_DURING_EXECUTION"


class DecisionChoice(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class ApprovalRequest:
    approval_id: str
    task_id: str
    session_id: str
    agent_id: str
    capability_name: str
    scope: str
    safe_summary: str
    payload_hash: str
    params_payload: str  # JSON canonique sérialisé
    requested_at: str
    expires_at: str
    requested_by: str = "system"
    status: ApprovalStatus = ApprovalStatus.PENDING
    decided_by: str | None = None
    decided_at: str | None = None
    decision_reason: str | None = None
    execution_state: ExecutionState = ExecutionState.NOT_STARTED
    consumed_at: str | None = None
    result_cache: str | None = None

    @classmethod
    def create(
        cls,
        task_id: str,
        session_id: str,
        agent_id: str,
        capability_name: str,
        scope: str,
        safe_summary: str,
        payload_hash: str,
        params_payload: str,
        ttl_seconds: int = 300,
        requested_by: str = "system",
        approval_id: str | None = None,
    ) -> ApprovalRequest:
        # Bornage du TTL : min 10s, max 1800s, défaut 300s
        clamped_ttl = max(10, min(1800, ttl_seconds))
        now_dt = datetime.now(UTC)
        req_at = now_dt.isoformat()
        exp_dt = datetime.fromtimestamp(now_dt.timestamp() + clamped_ttl, UTC)
        exp_at = exp_dt.isoformat()
        appr_id = approval_id or f"appr_{uuid.uuid4().hex[:12]}"

        return cls(
            approval_id=appr_id,
            task_id=task_id,
            session_id=session_id,
            agent_id=agent_id,
            capability_name=capability_name,
            scope=scope,
            safe_summary=safe_summary,
            payload_hash=payload_hash,
            params_payload=params_payload,
            requested_at=req_at,
            expires_at=exp_at,
            requested_by=requested_by,
            status=ApprovalStatus.PENDING,
            execution_state=ExecutionState.NOT_STARTED,
        )


@dataclass(frozen=True)
class ApprovalDecision:
    approval_id: str
    decision: DecisionChoice
    decided_by: str
    decided_at: str = field(default_factory=utc_now)
    reason: str | None = None
