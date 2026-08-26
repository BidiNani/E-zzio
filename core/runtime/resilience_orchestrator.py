"""
E-ZZIO V7.46 — Resilience & Chaos Orchestrator
Gère les stratégies de repli (Fallback), la récupération après panne et la supervision globale.
"""

import os
from core.runtime.circuit_breaker import kernel_circuit_breaker
from core.security.secret_redactor import secret_redactor
from core.security.immutable_audit import ImmutableAuditLedger
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
AUDIT_DIR = ROOT_DIR / "runtime" / "audit" / "discord"


class ResilienceOrchestrator:
    @staticmethod
    def handle_network_outage(error: Exception) -> str:
        kernel_circuit_breaker.record_failure()
        sanitized_err = secret_redactor.sanitize(str(error))

        # Journalisation de l'incident de sécurité / réseau
        ledger = ImmutableAuditLedger(AUDIT_DIR / "security_events.jsonl")
        ledger.append_event("NETWORK_OUTAGE_HANDLED", {"circuit_state": kernel_circuit_breaker.state, "error_snippet": sanitized_err[:100]})

        if kernel_circuit_breaker.state == "OPEN":
            return "⚠️ Noyau temporairement injoignable (Circuit Ouvert). Mode de protection actif."
        return f"❌ Erreur de communication transitoire : {sanitized_err}"

    @staticmethod
    def handle_vault_failure(error: Exception) -> dict:
        sanitized_err = secret_redactor.sanitize(str(error))

        ledger = ImmutableAuditLedger(AUDIT_DIR / "security_events.jsonl")
        ledger.append_event("VAULT_FAILURE_FALLBACK", {"error": sanitized_err, "action": "FALLBACK_TO_ENV_VARIABLES"})

        # Fallback sécurisé : bascule sur l'environnement si le Vault échoue
        fallback_token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
        return {"status": "DEGRADED_MODE", "fallback_active": True, "token_resolved": fallback_token is not None}


resilience_orchestrator = ResilienceOrchestrator()
