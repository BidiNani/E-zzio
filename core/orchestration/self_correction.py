"""
E-ZZIO Core V9.2 — Sovereign Autonomous Validation & Self-Correction Engine.

Fournit une capacité de validation empirique et d'auto-réparation bornée pour
les nœuds du TaskDAG et l'orchestration multi-agents E-ZZIO.

Cycle de vie :
EXECUTE -> VALIDATE -> DETECT FAILURE -> DIAGNOSE -> REPAIR -> RETEST -> VALIDATE -> COMPLETE
"""
from __future__ import annotations

import logging
import os
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from core.security.audit_ledger import AuditLedger

logger = logging.getLogger("AutonomousSelfCorrectionEngine")


class FailureType(StrEnum):
    ASSERTION_FAILED = "ASSERTION_FAILED"
    MISSING_ARTIFACT = "MISSING_ARTIFACT"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    EXECUTION_TIMEOUT = "EXECUTION_TIMEOUT"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    EMPTY_OUTPUT = "EMPTY_OUTPUT"
    UNHANDLED_EXCEPTION = "UNHANDLED_EXCEPTION"
    UNKNOWN = "UNKNOWN"


@dataclass
class DiagnosisReport:
    failure_type: FailureType
    root_cause: str
    details: str
    repairable: bool
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "failure_type": self.failure_type.value,
            "root_cause": self.root_cause,
            "details": self.details,
            "repairable": self.repairable,
            "timestamp": self.timestamp,
        }


@dataclass
class BoundedRepairPlan:
    attempt: int
    max_attempts: int
    diagnosis: DiagnosisReport
    repair_action: str
    remediation_prompt: str
    target_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "diagnosis": self.diagnosis.to_dict(),
            "repair_action": self.repair_action,
            "remediation_prompt": self.remediation_prompt,
            "target_path": self.target_path,
        }


@dataclass
class ValidationProof:
    is_valid: bool
    evidence_type: str
    details: str
    checked_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "evidence_type": self.evidence_type,
            "details": self.details,
            "checked_at": self.checked_at,
        }


class AutonomousSelfCorrectionEngine:
    """Engine de diagnostic d'échec et d'auto-réparation bornée pour les tâches multi-agents."""

    def __init__(self, audit_ledger: AuditLedger | None = None):
        self.audit_ledger = audit_ledger or AuditLedger()

    def diagnose_failure(
        self,
        task_id: str,
        output_or_error: Any,
        exception: Exception | None = None,
        context: dict[str, Any] | None = None,
    ) -> DiagnosisReport:
        """Analyse le résultat ou l'exception pour déterminer la cause racine et la réparabilité."""
        err_str = str(exception) if exception else ""
        out_str = str(output_or_error) if output_or_error is not None else ""
        combined = f"{err_str}\n{out_str}".strip()

        # 1. Security / Policy Blocked (Non-réparable de façon autonome sans approbation)
        if any(term in combined for term in ("[POLICY_DENIED]", "[RUNTIME POLICY BLOCKED]", "POLICY_DENIED", "AccessDenied")):
            return DiagnosisReport(
                failure_type=FailureType.POLICY_BLOCKED,
                root_cause="Operation blocked by security policy guard.",
                details=combined[:500],
                repairable=False,
            )

        # 2. Sortie vide
        if not combined or (isinstance(output_or_error, str) and not output_or_error.strip()):
            return DiagnosisReport(
                failure_type=FailureType.EMPTY_OUTPUT,
                root_cause="Subtask produced empty output or null response.",
                details="Empty response content received.",
                repairable=True,
            )

        # 3. Code / Syntax Error
        if any(term in combined for term in ("SyntaxError", "IndentationError", "JSONDecodeError", "invalid syntax")):
            return DiagnosisReport(
                failure_type=FailureType.SYNTAX_ERROR,
                root_cause="Syntax or parsing error detected in output or generated code.",
                details=combined[:500],
                repairable=True,
            )

        # 4. Fichier / Artefact Manquant
        if any(term in combined for term in ("FileNotFoundError", "MISSING_FILE", "Target file missing", "No such file")):
            return DiagnosisReport(
                failure_type=FailureType.MISSING_ARTIFACT,
                root_cause="Required target file or evidence artifact missing from workspace.",
                details=combined[:500],
                repairable=True,
            )

        # 5. Assertion Failed
        if any(term in combined for term in ("AssertionError", "ASSERTION_FAILED", "[EXIT_CODE:", "Validation failed", "test failed")):
            return DiagnosisReport(
                failure_type=FailureType.ASSERTION_FAILED,
                root_cause="Validation assertion failed or test execution returned non-zero code.",
                details=combined[:500],
                repairable=True,
            )

        # 6. Timeout
        if any(term in combined for term in ("TimeoutError", "asyncio.TimeoutError", "TIMED_OUT", "timed out")):
            return DiagnosisReport(
                failure_type=FailureType.EXECUTION_TIMEOUT,
                root_cause="Execution timed out.",
                details=combined[:500],
                repairable=True,
            )

        # Fallback General
        if exception:
            return DiagnosisReport(
                failure_type=FailureType.UNHANDLED_EXCEPTION,
                root_cause=f"Unhandled exception: {type(exception).__name__}",
                details=combined[:500],
                repairable=True,
            )

        return DiagnosisReport(
            failure_type=FailureType.UNKNOWN,
            root_cause="Subtask execution validation failed.",
            details=combined[:500],
            repairable=True,
        )

    def generate_repair_plan(
        self,
        task_id: str,
        diagnosis: DiagnosisReport,
        attempt: int,
        max_attempts: int,
        original_prompt: str,
    ) -> BoundedRepairPlan:
        """Génère un plan de réparation borné avec consignes correctives ciblées."""
        if not diagnosis.repairable or attempt > max_attempts:
            return BoundedRepairPlan(
                attempt=attempt,
                max_attempts=max_attempts,
                diagnosis=diagnosis,
                repair_action="FAIL_CLOSED",
                remediation_prompt="[FAIL-CLOSED] Non-repairable failure or repair retry limit reached.",
            )

        remediation_header = (
            f"[AUTO-REPAIR ATTEMPT {attempt}/{max_attempts}]\n"
            f"La tentative précédente pour la tâche '{task_id}' a échoué avec l'erreur :\n"
            f"- Type : {diagnosis.failure_type.value}\n"
            f"- Cause : {diagnosis.root_cause}\n"
            f"- Détails : {diagnosis.details}\n\n"
            f"CONSIGNE DE RÉPARATION :\n"
        )

        if diagnosis.failure_type == FailureType.SYNTAX_ERROR:
            action = "CORRECT_SYNTAX"
            guidance = "Corrige les erreurs de syntaxe, d'indentation ou le format JSON. Assure-toi que la sortie est syntaxiquement valide."
        elif diagnosis.failure_type == FailureType.MISSING_ARTIFACT:
            action = "CREATE_MISSING_ARTIFACT"
            guidance = "Assure-toi de générer ou créer explicitement le fichier attendu dans le workspace."
        elif diagnosis.failure_type == FailureType.ASSERTION_FAILED:
            action = "FIX_ASSERTION_FAILURE"
            guidance = "Analyse l'échec d'assertion ou du test et corrige l'implémentation pour satisfaire tous les critères de validation."
        elif diagnosis.failure_type == FailureType.EMPTY_OUTPUT:
            action = "REGENERATE_NON_EMPTY_RESPONSE"
            guidance = "Fournis une réponse complète, détaillée et non vide répondant directement à l'objectif."
        else:
            action = "GENERAL_REPAIR"
            guidance = "Applique une correction ciblée pour résoudre le problème identifié ci-dessus."

        full_prompt = f"{remediation_header}{guidance}\n\n[OBJECTIF INITIAL]\n{original_prompt}"

        return BoundedRepairPlan(
            attempt=attempt,
            max_attempts=max_attempts,
            diagnosis=diagnosis,
            repair_action=action,
            remediation_prompt=full_prompt,
        )

    def validate_proof(
        self,
        output: Any,
        expected_assertions: dict[str, Any] | None = None,
    ) -> ValidationProof:
        """Valide empiriquement la sortie et retourne la preuve de conformité."""
        if output is None:
            return ValidationProof(is_valid=False, evidence_type="NULL_OUTPUT", details="Output is None")

        out_str = str(output)
        if not out_str.strip():
            return ValidationProof(is_valid=False, evidence_type="EMPTY_OUTPUT", details="Output is whitespace")

        if "[POLICY_DENIED]" in out_str or "[RUNTIME POLICY BLOCKED]" in out_str:
            return ValidationProof(is_valid=False, evidence_type="POLICY_BLOCKED", details="Policy blocked execution")

        if expected_assertions:
            required_files = expected_assertions.get("required_files") or []
            for req_file in required_files:
                if not os.path.exists(req_file):
                    return ValidationProof(
                        is_valid=False,
                        evidence_type="MISSING_FILE",
                        details=f"Required file '{req_file}' does not exist on disk.",
                    )

            expected_contains = expected_assertions.get("contains") or []
            for item in expected_contains:
                if item not in out_str:
                    return ValidationProof(
                        is_valid=False,
                        evidence_type="MISSING_CONTENT",
                        details=f"Expected substring '{item}' not found in output.",
                    )

            min_len = expected_assertions.get("min_length", 1)
            if len(out_str) < min_len:
                return ValidationProof(
                    is_valid=False,
                    evidence_type="INSUFFICIENT_LENGTH",
                    details=f"Output length ({len(out_str)}) < min_length ({min_len})",
                )

        return ValidationProof(
            is_valid=True,
            evidence_type="EMPIRICAL_PROOF",
            details="Output passed all validation assertions.",
        )

    async def execute_with_self_correction(
        self,
        task_id: str,
        original_prompt: str,
        execution_fn: Callable[[str, BoundedRepairPlan | None], Coroutine[Any, Any, dict[str, Any]]],
        max_repair_retries: int = 2,
        expected_assertions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Exécute une sous-tâche avec boucle autonome de validation et réparation bornée.

        Chaîne :
        EXECUTE -> VALIDATE -> DETECT FAILURE -> DIAGNOSE -> REPAIR -> RETEST -> VALIDATE -> COMPLETE
        """
        attempt = 0
        repair_history: list[dict[str, Any]] = []
        current_repair_plan: BoundedRepairPlan | None = None
        current_prompt = original_prompt

        while attempt <= max_repair_retries:
            try:
                # 1. EXECUTE / RETEST
                res = await execution_fn(current_prompt, current_repair_plan)

                # 2. VALIDATE
                out_content = res.get("output") if isinstance(res, dict) else str(res)
                proof = self.validate_proof(out_content, expected_assertions=expected_assertions)

                if proof.is_valid:
                    # 8. COMPLETE (SUCCESS)
                    if not isinstance(res, dict):
                        res = {"output": str(res), "status": "SUCCESS"}
                    res["validated"] = True
                    res["validation_proof"] = proof.to_dict()

                    if repair_history:
                        res["self_correction_applied"] = True
                        res["repair_history"] = repair_history

                        try:
                            self.audit_ledger.record_event(
                                actor="AutonomousSelfCorrectionEngine",
                                action="NODE_SELF_CORRECTION_SUCCESS",
                                payload={
                                    "task_id": task_id,
                                    "attempts_used": attempt,
                                    "repair_history": repair_history,
                                    "proof": proof.to_dict(),
                                },
                                status="COMPLETED",
                            )
                        except Exception:
                            pass

                    return res

                # 3. DETECT FAILURE (Validation failed)
                diagnosis = self.diagnose_failure(
                    task_id=task_id,
                    output_or_error=out_content,
                    context={"proof": proof.to_dict()},
                )

            except Exception as exc:
                # 3. DETECT FAILURE (Exception thrown)
                diagnosis = self.diagnose_failure(
                    task_id=task_id,
                    output_or_error=str(exc),
                    exception=exc,
                )
                res = {"output": f"[ERROR] {exc}", "status": "FAILED"}

            # Log audit log on failure detection
            try:
                self.audit_ledger.record_event(
                    actor="AutonomousSelfCorrectionEngine",
                    action="NODE_FAILURE_DETECTED",
                    payload={
                        "task_id": task_id,
                        "attempt": attempt,
                        "diagnosis": diagnosis.to_dict(),
                    },
                    status="FAILURE_DETECTED",
                )
            except Exception:
                pass

            if not diagnosis.repairable or attempt >= max_repair_retries:
                # Retries exhausted or fail-closed -> FAILED
                try:
                    self.audit_ledger.record_event(
                        actor="AutonomousSelfCorrectionEngine",
                        action="NODE_SELF_CORRECTION_EXHAUSTED",
                        payload={
                            "task_id": task_id,
                            "attempts_used": attempt,
                            "diagnosis": diagnosis.to_dict(),
                        },
                        status="FAILED",
                    )
                except Exception:
                    pass
                raise RuntimeError(
                    f"Self-correction exhausted for task '{task_id}' after {attempt} repair attempts. "
                    f"Root cause: {diagnosis.root_cause} ({diagnosis.details})"
                )

            # 4. DIAGNOSE & 5. REPAIR PLAN
            attempt += 1
            repair_plan = self.generate_repair_plan(
                task_id=task_id,
                diagnosis=diagnosis,
                attempt=attempt,
                max_attempts=max_repair_retries,
                original_prompt=original_prompt,
            )

            repair_history.append({
                "attempt": attempt,
                "diagnosis": diagnosis.to_dict(),
                "repair_plan": repair_plan.to_dict(),
            })

            current_repair_plan = repair_plan
            current_prompt = repair_plan.remediation_prompt

        raise RuntimeError(f"Self-correction loop terminated unexpectedly for task '{task_id}'.")


self_correction_engine = AutonomousSelfCorrectionEngine()
