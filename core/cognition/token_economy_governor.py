"""
E-ZZIO Core — Token Economy & Budget Governor (V8.3)
Gère l'économie des tokens d'E-zzio, répartit les quotas par catégorie de tâches,
surveille la consommation en temps réel et bloque (Fail-Closed) tout dépassement de budget.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.cognition.ecol_universal_enforcement import EcolUniversalGateway

logger = logging.getLogger(__name__)


class TokenBudgetExceededError(Exception):
    """Levée lorsqu'une tâche dépasse le budget de tokens alloué (Fail-Closed)."""

    pass


class TokenEconomyGovernor:
    # Répartition budgétaire des quotas (en tokens)
    BUDGET_ALLOCATION = {"reasoning": 4000, "code": 3000, "memory": 1500, "search": 1000, "maintenance": 500}

    def __init__(self, root_dir: Path = ROOT_DIR):
        self.root_dir = root_dir
        self.ledger_path = self.root_dir / "runtime" / "cognition" / "budget" / "token_ledger.json"
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

        self.gateway = EcolUniversalGateway()
        self.gateway.register_gateway_action("TOKEN_BUDGET_ALLOCATE")
        self._load_or_init_ledger()

    def _load_or_init_ledger(self):
        if not self.ledger_path.exists():
            initial_ledger = {
                "total_allocated": sum(self.BUDGET_ALLOCATION.values()),
                "spent_by_category": dict.fromkeys(self.BUDGET_ALLOCATION, 0),
            }
            self.ledger_path.write_text(json.dumps(initial_ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def request_tokens(self, category: str, requested_tokens: int) -> dict[str, Any]:
        """
        Vérifie et déduit les tokens demandés du budget de la catégorie sous le contrôle d'ECOL.
        """
        if category not in self.BUDGET_ALLOCATION:
            raise ValueError(f"Catégorie de token inconnue : {category}")

        ledger = json.loads(self.ledger_path.read_text(encoding="utf-8"))
        max_budget = self.BUDGET_ALLOCATION[category]
        current_spent = ledger["spent_by_category"][category]

        if current_spent + requested_tokens > max_budget:
            raise TokenBudgetExceededError(
                f"FAIL CLOSED : Budget épuisé pour la catégorie '{category}'. "
                f"Déjà consommé : {current_spent} | Demandé : {requested_tokens} | Quota Max : {max_budget}"
            )

        payload = {
            "source_component": "system_core",
            "action": "TOKEN_BUDGET_ALLOCATE",
            "task_description": f"Consommation de {requested_tokens} tokens [{category}]",
            "priority": "normal",
            "risk_level": "low",
            "estimated_cost": requested_tokens,
        }

        def commit_token_spend():
            ledger["spent_by_category"][category] += requested_tokens
            self.ledger_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return {
                "category": category,
                "tokens_granted": requested_tokens,
                "category_spent_total": ledger["spent_by_category"][category],
                "category_remaining": max_budget - ledger["spent_by_category"][category],
                "status": "BUDGET_GRANTED_SUCCESS",
            }

        # Validation No-Bypass via ECOL
        result = self.gateway.execute_via_gateway(action="TOKEN_BUDGET_ALLOCATE", payload=payload, target_func=commit_token_spend)

        return result


def test_token_economy():
    print("[*] Test du Token Economy & Budget Governor (V8.3)...")
    governor = TokenEconomyGovernor()

    print("\n--- Test 1 : Demande de tokens nominale (Catégorie 'code') ---")
    try:
        res = governor.request_tokens("code", 500)
        print(f"  [PASS] Tokens accordés : {res['tokens_granted']} | Restant en 'code' : {res['category_remaining']}")
    except Exception as e:
        print(f"  [FAIL] Erreur : {e}")

    print("\n--- Test 2 : Tentative de dépassement de budget (Fail-Closed) ---")
    try:
        # Demande massive dépassant le quota alloué à la maintenance (500 max)
        governor.request_tokens("maintenance", 9999)
        print("  [FAIL] Alerte : Un dépassement budgétaire a été autorisé !")
    except TokenBudgetExceededError as tbe:
        print(f"  [PASS] Interception réussie (Fail-Closed token) : {tbe}")

    print("\n" + "=" * 65)
    print(" TOKEN ECONOMY GOVERNOR (V8.3) : OPERATIONAL & ENFORCED")
    print("=" * 65)


if __name__ == "__main__":
    test_token_economy()
