"""E-ZZIO Quality Gate — Single Canonical Completion Authority (CompletionGate).

Seul CompletionGate.evaluate() dispose de l'autorité canonique pour délivrer
un CompletionDecision avec accepted=True et proof_status="PROVEN".
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("CompletionGate")


@dataclass
class CompletionDecision:
    accepted: bool
    proof_status: str  # "PROVEN" if accepted else "REJECTED"
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "proof_status": self.proof_status,
            "rationale": self.rationale,
        }


class CompletionGate:
    """Canonical Completion Authority for E-ZZIO tasks and worker results."""

    def __init__(self, audit_ledger: Any | None = None) -> None:
        self.audit_ledger = audit_ledger

    def evaluate(
        self,
        task_id: str = "",
        worker_id: str = "",
        exit_code: int = 0,
        output: str = "",
        evidence: Any | None = None,
        forced_proof_status: str | None = None,
        validation_passed: bool = True,
        require_evidence: bool = False,
        **kwargs: Any,
    ) -> CompletionDecision:
        def _audit(decision: CompletionDecision) -> None:
            """Journalise TOUT outcome de completion, y compris les rejets anticipés
            (tentatives de PROVEN forcée notamment) — un rejet non tracé est une
            faille de gouvernance."""
            if self.audit_ledger is None:
                return
            try:
                payload = {
                    "task_id": task_id,
                    "worker_id": worker_id,
                    "accepted": decision.accepted,
                    "proof_status": decision.proof_status,
                }
                if hasattr(self.audit_ledger, "record"):
                    self.audit_ledger.record(
                        event_type="COMPLETION_EVALUATION",
                        details=payload,
                    )
                elif hasattr(self.audit_ledger, "record_event"):
                    # AuditLedger canonique E-ZZIO : journal scellé via record_event().
                    self.audit_ledger.record_event(
                        actor="completion_gate",
                        action="COMPLETION_EVALUATION",
                        payload=payload,
                        status="SUCCESS" if decision.accepted else "REJECTED",
                    )
            except Exception:
                pass

        if require_evidence and evidence is None and forced_proof_status != "PROVEN":
            decision = CompletionDecision(
                accepted=False,
                proof_status="REJECTED",
                rationale="Missing evidence artifact required for completion verification",
            )
            _audit(decision)
            return decision

        if forced_proof_status == "PROVEN" and (not validation_passed or exit_code != 0):
            decision = CompletionDecision(
                accepted=False,
                proof_status="REJECTED",
                rationale="Forced PROVEN rejected due to validation failure or non-zero exit code",
            )
            _audit(decision)
            return decision

        if exit_code == 0 and validation_passed:
            if evidence is not None or forced_proof_status == "PROVEN":
                decision = CompletionDecision(
                    accepted=True,
                    proof_status="PROVEN",
                    rationale="Execution validated with proof of work",
                )
            else:
                decision = CompletionDecision(
                    accepted=True,
                    proof_status="MEASURED",
                    rationale="Execution succeeded without explicit evidence artifact",
                )
        else:
            decision = CompletionDecision(
                accepted=False,
                proof_status="REJECTED",
                rationale=f"Execution failed with exit_code={exit_code}, validation={validation_passed}",
            )

        _audit(decision)
        return decision
