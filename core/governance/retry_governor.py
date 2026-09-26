"""
core/governance/retry_governor.py — Sovereign Retry Governor (OpenMuse adaptation).

Strictly distinguishes SAFE RETRY from POTENTIALLY DUPLICATIVE RETRY:
- SAFE RETRY: transient reads, LLM provider 429/500, pre-dispatch connection failures, idempotent local operations.
- DUPLICATIVE RISK: external writes with OUTCOME_UNKNOWN, email/payment/calendar/remote mutations with uncertain dispatch.
- Enforces fail-closed blocking: non-safe retries are prohibited without prior reconciliation.
- Respects existing Budget/Policy governance.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any


class RetryClassification(StrEnum):
    SAFE_RETRY = "SAFE_RETRY"
    DUPLICATIVE_RISK = "DUPLICATIVE_RISK"
    EXHAUSTED = "EXHAUSTED"
    UNNECESSARY = "UNNECESSARY"


class RetryGovernor:
    """Gouverneur des politiques de réessai pour prévenir les duplications d'effets externes."""

    READ_ACTION_PREFIXES = ("read", "get", "list", "query", "inspect", "check", "scan", "status")

    @classmethod
    def evaluate_retry(
        cls,
        action_type: str,
        is_external: bool,
        is_idempotent: bool,
        outcome_status: str,
        retry_count: int,
        max_retries: int = 2,
        error_context: dict[str, Any] | None = None,
    ) -> tuple[bool, RetryClassification, str]:
        """
        Détermine si une tâche peut être réessayée automatiquement en toute sécurité.
        Retourne (allowed, classification, reason).
        """
        # 1. Tâche déjà terminée avec succès
        if outcome_status in ("COMPLETED", "SUCCEEDED", "SUCCESS"):
            return False, RetryClassification.UNNECESSARY, "TASK_ALREADY_COMPLETED"

        # 2. Dépassement du quota de réessais
        if retry_count >= max_retries:
            return False, RetryClassification.EXHAUSTED, f"MAX_RETRIES_EXCEEDED ({retry_count}/{max_retries})"

        # 3. Actions externes non idempotentes avec résultat incertain
        if is_external and not is_idempotent:
            if outcome_status in ("OUTCOME_UNKNOWN", "UNKNOWN"):
                return (
                    False,
                    RetryClassification.DUPLICATIVE_RISK,
                    "RECONCILIATION_REQUIRED: external non-idempotent mutation in unknown state",
                )
            if error_context and error_context.get("dispatched") is True and not error_context.get("confirmed_not_applied"):
                return (
                    False,
                    RetryClassification.DUPLICATIVE_RISK,
                    "RECONCILIATION_REQUIRED: request was dispatched, potential duplicate execution",
                )

        # 4. Actions en lecture (toujours sûres)
        lower_action = action_type.lower()
        if any(lower_action.startswith(p) for p in cls.READ_ACTION_PREFIXES):
            return True, RetryClassification.SAFE_RETRY, "SAFE_READ_IDEMPOTENT_RETRY"

        # 5. Erreurs transitoires pré-dispatch (le réseau a échoué avant d'envoyer la requête)
        if error_context and error_context.get("dispatched") is False:
            return True, RetryClassification.SAFE_RETRY, "PRE_DISPATCH_TRANSIENT_FAILURE"

        # 6. Erreurs transitoires de modèles d'inférence (429, 500, timeout)
        error_code = (error_context or {}).get("status_code")
        if error_code in (429, 500, 502, 503, 504):
            return True, RetryClassification.SAFE_RETRY, f"PROVIDER_TRANSIENT_HTTP_{error_code}"

        # 7. Actions déclarées strictement idempotentes
        if is_idempotent:
            return True, RetryClassification.SAFE_RETRY, "SAFE_IDEMPOTENT_ACTION_RETRY"

        # 8. Cas par défaut pour effet externe incertain : fail-closed
        if is_external:
            return (
                False,
                RetryClassification.DUPLICATIVE_RISK,
                "FAIL_CLOSED: external operation cannot be safely retried without reconciliation",
            )

        # 9. Opération locale non externe
        return True, RetryClassification.SAFE_RETRY, "LOCAL_OPERATION_SAFE_RETRY"
