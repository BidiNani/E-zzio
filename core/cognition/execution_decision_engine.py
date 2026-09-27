"""E-ZZIO Core — Unified Model & Worker Execution Decision Engine.

Architectural Convergence Engine (Mission 21):
- Evaluates candidate models (ModelSpec / CanonicalModelRecord) and external/native workers (Hermes, Cline, PiG, Native).
- Enforces single E-ZZIO Master authority over execution decisions.
- Incorporates Jev / Ollaya local fast decision hints into deterministic evaluation.
- Ranks candidate targets based on capabilities, health, privacy/sovereignty, cost class, risk, and latency.
- Guaranteed fail-closed fallback to E-ZZIO Native Worker or local sovereign models.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal

from core.agent.agent_guard import AgentPolicyGuard
from core.agent.external_worker_contract import BaseWorkerAdapter, GovernedWorkerSelector
from core.cognition.model_router import ModelRouter
from core.routing.model_registry import CanonicalModelRecord, canonical_model_registry
from core.security.audit_ledger import AuditLedger

logger = logging.getLogger("ExecutionDecisionEngine")


@dataclass
class ExecutionCandidate:
    """Unified candidate for execution (either Model or Worker)."""

    candidate_id: str
    candidate_type: Literal["MODEL", "WORKER"]
    provider_or_adapter: str  # e.g. "ollama", "gemini", "groq", or worker name "hermes", "cline", "native"
    is_local: bool
    is_available: bool
    capabilities: list[str] = field(default_factory=list)
    score: float = 0.0
    rationale: str = ""


@dataclass
class ExecutionDecision:
    """Final decision output for an execution request."""

    execution_type: Literal["MODEL", "WORKER"]
    target_id: str
    provider: str
    is_local: bool
    score: float
    rationale: str
    fallback_target_id: str = "native"
    candidate_scores: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_type": self.execution_type,
            "target_id": self.target_id,
            "provider": self.provider,
            "is_local": self.is_local,
            "score": self.score,
            "rationale": self.rationale,
            "fallback_target_id": self.fallback_target_id,
            "candidate_scores": self.candidate_scores,
        }


class ExecutionDecisionEngine:
    """Master Decision Engine governing execution target selection across models and workers."""

    def __init__(
        self,
        workspace_root: str = r"G:\AI\E-zzio",
        model_router: ModelRouter | None = None,
        worker_selector: GovernedWorkerSelector | None = None,
        policy_guard: AgentPolicyGuard | None = None,
        audit_ledger: AuditLedger | None = None,
    ) -> None:
        self.workspace_root = workspace_root
        self.audit_ledger = audit_ledger or AuditLedger()
        self.policy_guard = policy_guard or AgentPolicyGuard(workspace_root=workspace_root)
        self.model_router = model_router or ModelRouter()
        self.worker_selector = worker_selector or GovernedWorkerSelector(
            workspace_root=self.workspace_root,
            audit_ledger=self.audit_ledger,
            policy_guard=self.policy_guard,
        )

    def evaluate_and_decide(
        self,
        task_type: str = "coding",
        objective: str = "",
        preferred_target: str | None = None,
        require_worker: bool = False,
        prefer_local: bool = False,
        budget_permits_cloud: bool = True,
        jev_hint: dict[str, Any] | None = None,
    ) -> ExecutionDecision:
        """Evaluates model and worker candidates, applying deterministic rules and Jev local hints.

        Returns a single unified ExecutionDecision under E-ZZIO Master authority.
        """
        candidates: list[ExecutionCandidate] = []
        task_lower = (task_type or "").lower()

        # 1. Evaluate Worker Candidates
        for w_name, adapter in self.worker_selector._workers.items():
            avail = adapter.is_available()
            w_score = 0.0
            w_caps = ["CODING", "TOOL_USE", "EXECUTION"]

            if w_name == "native":
                w_score = 50.0  # Safe baseline fallback
            elif avail:
                w_score = 80.0  # External worker boost when available

            # Preferred target match
            if preferred_target and preferred_target.lower() == w_name:
                w_score += 30.0

            # Jev hint boost if Jev recommends this worker
            if jev_hint and jev_hint.get("recommended_worker") == w_name:
                w_score += 35.0

            candidates.append(
                ExecutionCandidate(
                    candidate_id=w_name,
                    candidate_type="WORKER",
                    provider_or_adapter=w_name,
                    is_local=True if w_name == "native" else False,
                    is_available=avail,
                    capabilities=w_caps,
                    score=w_score if avail else -100.0,
                    rationale=f"Worker {w_name} (Available: {avail})",
                )
            )

        # 2. Evaluate Model Candidates (unless strict worker required)
        if not require_worker:
            model_route = self.model_router.select_engine(
                task_type=task_type,
                budget_permits_cloud=budget_permits_cloud,
                prefer_local=prefer_local,
            )

            if model_route.get("status") != "FAIL_CLOSED" and model_route.get("model"):
                m_model = model_route["model"]
                m_prov = model_route["provider"]
                m_is_local = model_route.get("is_local", False)

                m_score = 70.0
                if prefer_local and m_is_local:
                    m_score += 25.0
                if preferred_target and preferred_target.lower() in (m_model.lower(), m_prov.lower()):
                    m_score += 30.0
                if jev_hint and jev_hint.get("recommended_model") == m_model:
                    m_score += 15.0

                candidates.append(
                    ExecutionCandidate(
                        candidate_id=m_model,
                        candidate_type="MODEL",
                        provider_or_adapter=m_prov,
                        is_local=m_is_local,
                        is_available=True,
                        capabilities=["TEXT", "CODING", "REASONING"],
                        score=m_score,
                        rationale=f"Model {m_model} via provider {m_prov}",
                    )
                )

        # 3. Sort candidates by score descending
        valid_candidates = [c for c in candidates if c.is_available and c.score > 0]
        if not valid_candidates:
            # Absolute Fail-Closed Fallback -> E-ZZIO Native Worker
            logger.warning("[ExecutionDecisionEngine] All candidates unavailable or invalid. Failing closed to Native Worker.")
            return ExecutionDecision(
                execution_type="WORKER",
                target_id="native",
                provider="native",
                is_local=True,
                score=1.0,
                rationale="Fail-closed fallback to E-ZZIO Native Worker",
                fallback_target_id="native",
                candidate_scores=[{"id": c.candidate_id, "score": c.score} for c in candidates],
            )

        top_candidate = max(valid_candidates, key=lambda c: c.score)

        # Log decision in AuditLedger
        self.audit_ledger.record_event(
            actor="ezzio-master",
            action="EXECUTION_TARGET_DECIDED",
            payload={
                "task_type": task_type,
                "selected_target": top_candidate.candidate_id,
                "target_type": top_candidate.candidate_type,
                "provider": top_candidate.provider_or_adapter,
                "score": top_candidate.score,
                "jev_hint_applied": bool(jev_hint),
            },
            status="SUCCESS",
        )

        return ExecutionDecision(
            execution_type=top_candidate.candidate_type,
            target_id=top_candidate.candidate_id,
            provider=top_candidate.provider_or_adapter,
            is_local=top_candidate.is_local,
            score=top_candidate.score,
            rationale=top_candidate.rationale,
            fallback_target_id="native",
            candidate_scores=[{"id": c.candidate_id, "score": c.score} for c in candidates],
        )
