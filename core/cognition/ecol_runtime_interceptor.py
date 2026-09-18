"""
E-ZZIO Core — Governor Runtime Interceptor (V7.67)
Fournit un mécanisme d'interception actif (décorateur @ecol_guarded) pour
contraindre l'exécution réelle des outils, scripts et dispatchers LLM
aux verdicts du Cognitive Governor (ALLOW / DENY / REVIEW).
"""

import functools
import logging
import sys
from collections.abc import Callable
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.cognition.cognitive_governor import LedgerSecurityError
from core.cognition.ecol_runtime_contract import ContractValidationError, EcolRuntimeContract

logger = logging.getLogger(__name__)


class ExecutionBlockedByEcolError(Exception):
    """Levée lorsqu'un composant tente d'exécuter une action bloquée par le gouverneur (DENY)."""

    pass


class EcolRuntimeInterceptor:
    def __init__(self, contract: EcolRuntimeContract = None):
        self.contract = contract if contract is not None else EcolRuntimeContract()

    def guarded_execution(
        self,
        source_component: str = "tool_runner",
        action: str = "EXECUTE_TOOL",
        priority: str = "normal",
        risk_level: str = "low",
        estimated_cost: int = 100,
    ):
        """
        Décorateur d'interception active pour transformer une fonction d'exécution
        en une tâche gouvernée et scellée dans le Ledger ECOL.
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                task_description = f"Exécution de la fonction '{func.__name__}'"

                payload = {
                    "source_component": source_component,
                    "action": action,
                    "task_description": task_description,
                    "priority": priority,
                    "risk_level": risk_level,
                    "estimated_cost": estimated_cost,
                    "context_metadata": {"module": func.__module__, "qualname": func.__qualname__},
                }

                logger.info(f"[ECOL INTERCEPTOR] Évaluation de l'action : {action} ({func.__name__})...")

                try:
                    # 1. Évaluation synchrone par le contrat ECOL (V7.66)
                    eval_result = self.contract.evaluate_request(payload)
                    decision = eval_result.get("decision")
                    transaction_id = eval_result.get("transaction_id")

                    if decision == "DENY":
                        reason = eval_result.get("reason", "Raison non spécifiée.")
                        raise ExecutionBlockedByEcolError(
                            f"FAIL CLOSED : Exécution bloquée par le gouverneur pour '{func.__name__}'. "
                            f"Motif : {reason} (TX: {transaction_id})"
                        )

                    if decision == "REVIEW":
                        logger.warning(f"[ECOL REVIEW] Action '{func.__name__}' placée en révision manuelle (TX: {transaction_id})")
                        # Optionnel : bloquer ou rétrograder en mode strict
                        raise ExecutionBlockedByEcolError(
                            f"FAIL CLOSED : L'action '{func.__name__}' exige une révision (REVIEW) non levée."
                        )

                    logger.info(f"[ECOL ALLOW] Autorisation accordée pour '{func.__name__}' (TX: {transaction_id})")

                    # 2. Exécution effective de la cible si ALLOW
                    return func(*args, **kwargs)

                except (ContractValidationError, LedgerSecurityError) as sec_err:
                    logger.error(f"[ECOL SECURITY BREACH] Violation critique interceptée : {sec_err}")
                    raise ExecutionBlockedByEcolError(f"Verrouillage de sécurité actif : {sec_err}") from sec_err

            return wrapper

        return decorator


def test_runtime_interceptor():
    print("[*] Test du Governor Runtime Interceptor (V7.67)...")
    interceptor = EcolRuntimeInterceptor()

    # Définition d'un outil simulé protégé par ECOL
    @interceptor.guarded_execution(
        source_component="tool_runner", action="EXECUTE_PYTHON_SCRIPT", priority="normal", risk_level="low", estimated_cost=200
    )
    def target_safe_tool(script_name: str) -> str:
        print(f"    -> [OUTIL EFFECTIF] Exécution du script : {script_name}")
        return f"Succès de l'exécution de {script_name}"

    # Test 1 : Exécution autorisée (Budget nominal)
    print("\n--- Test 1 : Exécution d'un outil sous budget nominal ---")
    try:
        res = target_safe_tool("optimizer_v1.py")
        print(f"  [PASS] Résultat retourné : {res}")
    except Exception as e:
        print(f"  [FAIL] Erreur inattendue : {e}")

    # Test 2 : Tentative d'exécution d'une tâche à coût massif provoquant un DENY (Fail-Closed)
    @interceptor.guarded_execution(
        source_component="tool_runner",
        action="EXECUTE_MASSIVE_DELETION",
        priority="low",
        risk_level="high",
        estimated_cost=999999,  # Dépassement massif du budget global
    )
    def target_dangerous_tool() -> str:
        print("    -> [OUTIL EFFECTIF] Cette ligne ne doit JAMAIS s'exécuter !")
        return "Danger"

    print("\n--- Test 2 : Blocage actif d'une tâche à risque / coût excessif (Fail-Closed) ---")
    try:
        target_dangerous_tool()
        print("  [FAIL] Alerte : L'outil dangereux s'est exécuté sans encombre !")
    except ExecutionBlockedByEcolError as e:
        print(f"  [PASS] Interception réussie (FAIL CLOSED actif) : {e}")

    print("\n" + "=" * 65)
    print(" GOVERNOR RUNTIME INTERCEPTOR (V7.67) : DEPLOYED & ENFORCED")
    print("=" * 65)


if __name__ == "__main__":
    test_runtime_interceptor()
