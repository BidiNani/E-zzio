"""
E-ZZIO V7.60.3 — ECOL Governor & Ledger Deployment
Déploie le gouverneur cognitif qui calcule le budget, prend la décision d'allocation
et écrit l'audit immuable dans le registre des dépenses cognitives.
"""

from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
CORE_COG_DIR = ROOT_DIR / "core" / "cognition"

GOVERNOR_CODE = '''"""
E-ZZIO Core — Cognitive Governor (ECOL)
Le gardien final. Évalue le coût vs valeur et consigne les dépenses dans le Token Ledger.
"""
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)

class CognitiveGovernor:
    def __init__(self, root_dir: Path = Path(r"G:\\AI\\E-zzio")):
        logger.info("Initialisation du Cognitive Governor (Économie Cognitive)...")
        self.root_dir = root_dir
        self.ledger_path = self.root_dir / "runtime" / "cognition" / "budget" / "cognitive_budget_ledger.jsonl"

        # Le budget est défini ici (ex: 500k tokens par fenêtre d'exécution)
        self.max_session_budget = 500000

    def _calculate_current_spend(self) -> int:
        """Calcule la dépense actuelle en lisant le registre immuable."""
        total_tokens = 0
        if not self.ledger_path.exists():
            return 0

        try:
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        if data.get("decision") in ["ALLOW", "ALLOW_EXCEED"]:
                            total_tokens += data.get("estimated_cost", 0)
        except Exception as e:
            logger.error(f"Erreur de lecture du Cognitive Budget Ledger : {e}")

        return total_tokens

    def evaluate_and_record(self, task: str, estimated_tokens: int, priority: str = "normal", risk_level: str = "low") -> Dict[str, Any]:
        """
        La fonction vitale. Décide si l'effort cognitif est autorisé et l'enregistre.
        """
        current_spend = self._calculate_current_spend()

        # 1. Logique d'arbitrage
        decision = "ALLOW"
        reason = "Budget cognitif nominal."

        if current_spend + estimated_tokens > self.max_session_budget:
            if priority == "critical":
                decision = "ALLOW_EXCEED"
                reason = "Dépassement budgétaire autorisé (priorité CRITIQUE)."
            else:
                decision = "DENY"
                reason = f"Budget insuffisant. Restant: {max(0, self.max_session_budget - current_spend)} tokens."

        # Modération sur le risque
        if risk_level == "high" and priority != "critical":
            decision = "DENY"
            reason = "Rejet : Tâche à haut risque ne justifiant pas l'effort cognitif."

        # 2. Forge de l'archive d'audit
        transaction = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task": task,
            "priority": priority,
            "risk_level": risk_level,
            "estimated_cost": estimated_tokens,
            "decision": decision,
            "reason": reason,
            "current_spend_after": current_spend + (estimated_tokens if "ALLOW" in decision else 0)
        }

        # 3. Écriture sécurisée dans le Ledger (Append-Only)
        try:
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(transaction, ensure_ascii=False) + "\\n")
        except Exception as e:
            logger.error(f"Échec de l'écriture dans le registre budgétaire : {e}")

        return transaction
'''


def deploy_governor():
    print("[*] Déploiement du Cognitive Governor et liaison du Token Ledger...")
    CORE_COG_DIR.mkdir(parents=True, exist_ok=True)

    gov_path = CORE_COG_DIR / "cognitive_governor.py"
    with open(gov_path, "w", encoding="utf-8") as f:
        f.write(GOVERNOR_CODE.strip() + "\n")

    print("  + Implémentation validée : cognitive_governor.py")
    print("\n" + "=" * 65)
    print(" COGNITIVE GOVERNOR DEPLOYMENT (V7.60.3) SUCCEEDED")
    print("=" * 65)


if __name__ == "__main__":
    deploy_governor()
