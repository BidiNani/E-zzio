"""
core/reliability/reconciliation.py — Sovereign Reconciliation Engine (OpenMuse adaptation).

Resolves OUTCOME_UNKNOWN tasks following interrupted external side-effects:
- Inspects existing evidence & receipts
- Compares operation_id and canonical payload_hash
- Queries target state via deterministic probes when available
- Transitions strictly to RESOLVED_COMPLETED, RESOLVED_NOT_DISPATCHED (safe retry), or BLOCKED.
- Never silently converts UNKNOWN to SUCCESS or FAILED without proof.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from core.orchestration.dag import DAGExecutionStatus, DAGNode
from core.reliability.action_identity import compute_payload_hash

logger = logging.getLogger("ReconciliationEngine")


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class ReconciliationOutcome(StrEnum):
    RESOLVED_COMPLETED = "RESOLVED_COMPLETED"
    RESOLVED_NOT_DISPATCHED = "RESOLVED_NOT_DISPATCHED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ReconciliationReport:
    operation_id: str
    task_id: str
    outcome: ReconciliationOutcome
    reason: str
    evidence_found: dict[str, Any] = field(default_factory=dict)
    reconciled_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "task_id": self.task_id,
            "outcome": self.outcome.value,
            "reason": self.reason,
            "evidence_found": self.evidence_found,
            "reconciled_at": self.reconciled_at,
        }


class ReconciliationEngine:
    """
    Moteur de réconciliation souverain sous gouvernance d'EzzioMaster.
    Évite les doubles dispatches et résout les incertitudes après crash ou déconnexion.
    """

    def __init__(self, audit_ledger: Any | None = None) -> None:
        self.audit_ledger = audit_ledger
        self._known_receipts: dict[str, dict[str, Any]] = {}

    def register_receipt(
        self,
        operation_id: str,
        task_id: str,
        payload_hash: str,
        outcome: str,
        receipt_data: dict[str, Any] | None = None,
    ) -> None:
        """Enregistre un reçu d'opération avec hash de contrôle."""
        self._known_receipts[operation_id] = {
            "operation_id": operation_id,
            "task_id": task_id,
            "payload_hash": payload_hash,
            "outcome": outcome,
            "recorded_at": utc_now(),
            "data": receipt_data or {},
        }

    def reconcile_node(
        self,
        node: DAGNode,
        external_probe: Callable[[DAGNode], dict[str, Any] | None] | None = None,
    ) -> ReconciliationReport:
        """
        Réconcilie un nœud DAG dont le statut est OUTCOME_UNKNOWN.
        1. Vérifie si un reçu local valide existe déjà.
        2. Sinon, interroge la cible externe via la fonction probe (si disponible).
        3. Si aucune preuve formelle n'existe, bloque le nœud (BLOCKED) pour empêcher tout retry dangereux.
        """
        # Génération ou vérification de l'operation_id et du payload_hash
        payload = node.payload or {}
        p_hash = node.payload_hash or compute_payload_hash(payload)
        op_id = node.operation_id or f"op_{p_hash[:16]}"
        node.operation_id = op_id
        node.payload_hash = p_hash

        # 1. Vérification dans les reçus locaux
        if op_id in self._known_receipts:
            receipt = self._known_receipts[op_id]
            if receipt.get("payload_hash") == p_hash and receipt.get("outcome") in ("SUCCESS", "COMPLETED"):
                node.status = DAGExecutionStatus.COMPLETED
                node.reconciliation_status = ReconciliationOutcome.RESOLVED_COMPLETED.value
                node.result = receipt.get("data", {})
                report = ReconciliationReport(
                    operation_id=op_id,
                    task_id=node.task_id,
                    outcome=ReconciliationOutcome.RESOLVED_COMPLETED,
                    reason="Matched confirmed local receipt with identical payload hash",
                    evidence_found=receipt,
                )
                self._record_audit(node, report)
                return report

        # 2. Sonde externe (probe) si fournie
        if external_probe is not None:
            try:
                probe_res = external_probe(node)
                if probe_res and probe_res.get("executed") is True:
                    # L'action a bien eu lieu sur la cible
                    node.status = DAGExecutionStatus.COMPLETED
                    node.reconciliation_status = ReconciliationOutcome.RESOLVED_COMPLETED.value
                    node.result = probe_res.get("result", {})
                    report = ReconciliationReport(
                        operation_id=op_id,
                        task_id=node.task_id,
                        outcome=ReconciliationOutcome.RESOLVED_COMPLETED,
                        reason="External probe confirmed mutation was executed on target",
                        evidence_found=probe_res,
                    )
                    self._record_audit(node, report)
                    return report

                if probe_res and probe_res.get("not_dispatched") is True:
                    # La cible confirme formellement que l'action n'a pas été reçue -> Safe retry
                    node.status = DAGExecutionStatus.READY
                    node.reconciliation_status = ReconciliationOutcome.RESOLVED_NOT_DISPATCHED.value
                    report = ReconciliationReport(
                        operation_id=op_id,
                        task_id=node.task_id,
                        outcome=ReconciliationOutcome.RESOLVED_NOT_DISPATCHED,
                        reason="External probe confirmed mutation was never applied to target",
                        evidence_found=probe_res,
                    )
                    self._record_audit(node, report)
                    return report

            except Exception as e:
                logger.warning(
                    "[Reconciliation] Erreur lors de l'appel de la sonde externe pour %s: %s",
                    node.task_id,
                    e,
                )

        # 3. Absence de preuve déterminante -> BLOCKED (Fail-closed)
        node.status = DAGExecutionStatus.BLOCKED
        node.reconciliation_status = ReconciliationOutcome.BLOCKED.value
        report = ReconciliationReport(
            operation_id=op_id,
            task_id=node.task_id,
            outcome=ReconciliationOutcome.BLOCKED,
            reason="Ambiguous external outcome cannot be resolved; duplicate retry prevented",
            evidence_found={"checked_receipt": op_id in self._known_receipts},
        )
        self._record_audit(node, report)
        return report

    def _record_audit(self, node: DAGNode, report: ReconciliationReport) -> None:
        if self.audit_ledger and hasattr(self.audit_ledger, "record_event"):
            try:
                self.audit_ledger.record_event(
                    actor="ReconciliationEngine",
                    action=f"RECONCILIATION_{report.outcome.value}",
                    payload={
                        "task_id": node.task_id,
                        "operation_id": report.operation_id,
                        "outcome": report.outcome.value,
                        "reason": report.reason,
                    },
                    status=report.outcome.value,
                )
            except Exception as e:
                logger.error("[Reconciliation] Erreur d'audit: %s", e)
