"""
E-ZZIO Core — Universal Enforcement Layer (V7.70)
Garantit l'immutabilité du contrat runtime (via manifeste et SHA-256),
impose une passerelle d'exécution universelle (No Bypass) et journalise
les tentatives d'évolution dans un ledger dédié.
"""

import hashlib
import json
import logging
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.cognition.ecol_runtime_contract import EcolRuntimeContract

logger = logging.getLogger(__name__)


class UniversalEnforcementError(Exception):
    """Levée pour toute infraction à la politique universelle ou altération du contrat (Fail-Closed)."""

    pass


class EcolUniversalGateway:
    def __init__(self, root_dir: Path = ROOT_DIR):
        self.root_dir = root_dir
        self.contracts_dir = self.root_dir / "runtime" / "ecol" / "contracts"
        self.evolution_ledger_dir = self.root_dir / "runtime" / "ecol" / "evolution_ledger"

        self.contracts_dir.mkdir(parents=True, exist_ok=True)
        self.evolution_ledger_dir.mkdir(parents=True, exist_ok=True)

        self.contract = EcolRuntimeContract()
        self._verify_contract_integrity_at_boot()
        self._registered_gateway_actions = set()

    def _verify_contract_integrity_at_boot(self):
        """Vérifie que le contrat runtime n'a pas subi de dérive par rapport à son manifeste scellé."""
        manifest_path = self.contracts_dir / "contract_manifest.json"
        contract_source_path = self.root_dir / "core" / "cognition" / "ecol_runtime_contract.py"

        if not manifest_path.exists():
            # Initialisation du scellement du contrat si premier boot
            logger.info("Scellement initial du contrat runtime V7.70...")
            if not contract_source_path.exists():
                raise UniversalEnforcementError("FAIL CLOSED : Fichier source ecol_runtime_contract.py introuvable.")

            sha256_hash = hashlib.sha256(contract_source_path.read_bytes()).hexdigest().lower()
            manifest_data = {
                "contract_filename": "ecol_runtime_contract.py",
                "sha256": sha256_hash,
                "sealed_at_utc": datetime.now(UTC).isoformat(),
                "status": "SEALED",
            }
            manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return

        # Vérification d'intégrité
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            expected_hash = manifest["sha256"]
            actual_hash = hashlib.sha256(contract_source_path.read_bytes()).hexdigest().lower()

            if actual_hash != expected_hash:
                raise UniversalEnforcementError(
                    f"FAIL CLOSED CRITIQUE : Altération détectée sur le contrat runtime ! Attendu: {expected_hash} | Trouvé: {actual_hash}"
                )
            logger.info("[OK] Intégrité du contrat runtime V7.70 vérifiée (Zero Drift).")
        except Exception as e:
            raise UniversalEnforcementError(f"FAIL CLOSED : Échec de la vérification du contrat runtime : {e}")

    def register_gateway_action(self, action_name: str):
        """Enregistre une action comme 'Passerelle Obligatoire' (Anti-Bypass)."""
        self._registered_gateway_actions.add(action_name)

    def execute_via_gateway(self, action: str, payload: dict[str, Any], target_func: Callable, *args, **kwargs) -> Any:
        """
        Passerelle d'exécution universelle (No Bypass).
        Interdit toute exécution si l'action n'est pas enregistrée ou si le gouverneur refuse.
        """
        if action not in self._registered_gateway_actions:
            raise UniversalEnforcementError(
                f"FAIL CLOSED POLICY [NO BYPASS] : L'action '{action}' n'est pas enregistrée dans la passerelle universelle."
            )

        # Journalisation spécifique dans l'Evolution / Execution Ledger
        attempt_record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "action": action,
            "source": payload.get("source_component", "unknown"),
            "status": "PENDING_EVALUATION",
        }

        try:
            # Évaluation par le contrat sécurisé
            eval_result = self.contract.evaluate_request(payload)
            decision = eval_result.get("decision")
            transaction_id = eval_result.get("transaction_id")

            attempt_record["transaction_id"] = transaction_id
            attempt_record["decision"] = decision

            if decision != "ALLOW":
                attempt_record["status"] = "BLOCKED_BY_GOVERNOR"
                self._log_evolution_attempt(attempt_record)
                raise UniversalEnforcementError(
                    f"FAIL CLOSED : Exécution universelle bloquée pour '{action}'. "
                    f"Motif : {eval_result.get('reason')} (TX: {transaction_id})"
                )

            attempt_record["status"] = "APPROVED_AND_EXECUTED"
            self._log_evolution_attempt(attempt_record)

            # Exécution effective
            return target_func(*args, **kwargs)

        except Exception as e:
            if not isinstance(e, UniversalEnforcementError):
                attempt_record["status"] = f"ERROR: {str(e)}"
                self._log_evolution_attempt(attempt_record)
            raise

    def _log_evolution_attempt(self, record: dict):
        """Enregistre l'essai dans un fichier journalier indépendant (Evolution Ledger)."""
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        ledger_file = self.evolution_ledger_dir / f"evolution_audit_{date_str}.jsonl"

        with open(ledger_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")


def test_universal_enforcement():
    print("[*] Test de la V7.70 (Universal Enforcement & Contract Sealing)...")
    gateway = EcolUniversalGateway()

    # Enregistrement d'une action officielle
    action_key = "EXECUTE_GOVERNED_SKILL"
    gateway.register_gateway_action(action_key)

    # Fonction cible autorisée
    def dummy_skill_runner(skill_name: str):
        print(f"    -> [GATEWAY EXECUTION] Lancement effectif de la compétence : {skill_name}")
        return f"Compétence {skill_name} exécutée avec succès."

    # Test 1 : Exécution via la passerelle (No Bypass) sous contrat valide
    print("\n--- Test 1 : Exécution via la passerelle universelle (ALLOW) ---")
    payload = {
        "source_component": "evolution_engine",
        "action": action_key,
        "task_description": "Exécution d'une compétence certifiée",
        "priority": "normal",
        "risk_level": "low",
        "estimated_cost": 150,
    }

    try:
        res = gateway.execute_via_gateway(action_key, payload, dummy_skill_runner, "Advanced_Optimizer")
        print(f"  [PASS] Résultat : {res}")
    except Exception as e:
        print(f"  [FAIL] {e}")

    # Test 2 : Tentative de contournement par une action non enregistrée (Bypass interdit)
    print("\n--- Test 2 : Tentative de contournement (Action non enregistrée -> FAIL CLOSED) ---")
    try:
        gateway.execute_via_gateway("UNREGISTERED_ROGUE_ACTION", payload, dummy_skill_runner, "Rogue")
        print("  [FAIL] Alerte : Une action non enregistrée a contourné la passerelle !")
    except UniversalEnforcementError as uee:
        print(f"  [PASS] Interception anti-bypass réussie : {uee}")

    print("\n" + "=" * 65)
    print(" UNIVERSAL ENFORCEMENT LAYER (V7.70) : DEPLOYED & SEALED")
    print("=" * 65)


if __name__ == "__main__":
    test_universal_enforcement()
