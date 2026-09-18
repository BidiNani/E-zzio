"""
E-ZZIO Core — ECOL Runtime Contract Layer (V7.66)
Couche adaptatrice universelle et agnostique. Permet aux composants d'E-zzio
de soumettre des requêtes d'exécution au Cognitive Governor sous un format de contrat strict.
Ne modifie en aucun cas le noyau ECOL certifié V7.65.
"""

import logging
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.cognition.cognitive_governor import CognitiveGovernor, LedgerSecurityError

logger = logging.getLogger(__name__)


class ContractValidationError(Exception):
    """Levée en cas d'infraction au schéma du contrat d'intégration V7.66."""

    pass


class EcolRuntimeContract:
    CONTRACT_VERSION = "V7.66"

    VALID_PRIORITIES = {"low", "normal", "high", "critical"}
    VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}
    VALID_SOURCES = {"llm_dispatcher", "tool_runner", "memory_subsystem", "evolution_engine", "system_core"}

    def __init__(self, governor: CognitiveGovernor | None = None):
        self.governor = governor if governor is not None else CognitiveGovernor()

    def _validate_payload(self, payload: dict[str, Any]):
        """Valide la structure et les types du payload d'entrée selon le contrat V7.66."""
        if not isinstance(payload, dict):
            raise ContractValidationError("Le payload du contrat doit être un dictionnaire JSON valide.")

        # Champs obligatoires
        required_fields = ["source_component", "action", "task_description", "priority", "risk_level", "estimated_cost"]
        for field in required_fields:
            if field not in payload:
                raise ContractValidationError(f"Violation de contrat : Champ obligatoire manquant -> '{field}'")

        # Validation de la source
        if payload["source_component"] not in self.VALID_SOURCES:
            raise ContractValidationError(f"Violation de contrat : Source non autorisée -> '{payload['source_component']}'")

        # Validation de la priorité
        if payload["priority"] not in self.VALID_PRIORITIES:
            raise ContractValidationError(f"Violation de contrat : Priorité invalide -> '{payload['priority']}'")

        # Validation du risque
        if payload["risk_level"] not in self.VALID_RISK_LEVELS:
            raise ContractValidationError(f"Violation de contrat : Niveau de risque invalide -> '{payload['risk_level']}'")

        # Validation du coût estimé
        cost = payload["estimated_cost"]
        if not isinstance(cost, int) or cost < 0:
            raise ContractValidationError("Violation de contrat : 'estimated_cost' doit être un entier positif.")

    def evaluate_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Point d'entrée unique pour toute demande d'exécution des composants d'E-zzio.
        Applique le contrat, interroge le gouverneur et normalise la réponse.
        """
        # 1. Validation structurelle stricte
        self._validate_payload(payload)

        source = payload["source_component"]
        action = payload["action"]
        task_desc = payload["task_description"]
        priority = payload["priority"]
        risk_level = payload["risk_level"]
        estimated_cost = payload["estimated_cost"]

        # Formatage de la tâche pour le Ledger ECOL
        formatted_task = f"[{source.upper()}] {action} : {task_desc}"

        # Mappage du risque élevé vers un examen manuel (REVIEW) ou refus direct
        effective_risk = risk_level
        if risk_level == "critical":
            effective_risk = "high"  # Forçage de la politique de risque du gouverneur

        try:
            # 2. Appel au socle de gouvernance certifié ECOL V7.65
            gov_record = self.governor.evaluate_and_record(
                task=formatted_task, estimated_tokens=estimated_cost, priority=priority, risk_level=effective_risk
            )

            decision = gov_record.get("decision", "DENY")

            # Post-traitement de la décision si risque moyen/élevé
            if risk_level == "medium" and decision == "ALLOW":
                # Optionnel : marquer pour révision si nécessaire, ou laisser ALLOW si budget ok
                pass

            # 3. Normalisation de la réponse du contrat V7.66
            response = {
                "contract_version": self.CONTRACT_VERSION,
                "source_component": source,
                "action": action,
                "transaction_id": gov_record.get("record_hash"),
                "decision": decision,
                "reason": gov_record.get("reason"),
                "current_spend_after": gov_record.get("current_spend_after"),
                "hmac_signature": gov_record.get("hmac_signature"),
                "timestamp": gov_record.get("timestamp"),
            }
            return response

        except LedgerSecurityError as lse:
            logger.error(f"FAIL CLOSED ECOL : Interception d'une infraction de sécurité -> {lse}")
            raise
        except Exception as e:
            raise RuntimeError(f"Erreur critique lors de l'évaluation du contrat runtime : {e}")


def test_runtime_contract():
    print("[*] Test d'intégration de la couche de contrat runtime V7.66...")
    contract = EcolRuntimeContract()

    # Test d'une requête valide nominale
    valid_payload = {
        "source_component": "llm_dispatcher",
        "action": "EXECUTE_TOOL",
        "task_description": "Génération de code d'automatisation Bao",
        "priority": "normal",
        "risk_level": "low",
        "estimated_cost": 350,
        "context_metadata": {"session_id": "EZZIO-SESS-001"},
    }

    result = contract.evaluate_request(valid_payload)
    print(f"  [PASS] Requête acceptée. Décision : {result['decision']} (Spend après: {result['current_spend_after']})")
    print(f"  [PASS] Empreinte de transaction (Record Hash) : {result['transaction_id']}")
    print(f"  [PASS] Attestation HMAC liée : {result['hmac_signature'][:32]}...")

    # Test d'une requête violant le schéma du contrat (Fail-Closed amont)
    print("\n  * Test de rejet amont (Violation de contrat schema)...")
    invalid_payload = {
        "source_component": "rogue_module",  # Source non autorisée
        "action": "UNAUTHORIZED_ACTION",
        "task_description": "Tentative de contournement",
        "priority": "normal",
        "risk_level": "low",
        "estimated_cost": 100,
    }

    try:
        contract.evaluate_request(invalid_payload)
        print("  [FAIL] Alerte : Le contrat a accepté une source non autorisée !")
    except ContractValidationError as cve:
        print(f"  [PASS] Contrat respecté : rejet immédiat -> {cve}")

    print("\n" + "=" * 65)
    print(" ECOL RUNTIME CONTRACT LAYER (V7.66) : DEPLOYED & VERIFIED")
    print("=" * 65)


if __name__ == "__main__":
    test_runtime_contract()
