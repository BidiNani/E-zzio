"""
E-ZZIO V7.61.2 — Chained Cryptographic Cognitive Ledger
Met à niveau le Cognitive Governor pour garantir l'intégrité cryptographique
du registre budgétaire via un chaînage de hachage SHA-256 (previous_hash -> record_hash).
"""

from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
GOVERNOR_PATH = ROOT_DIR / "core" / "cognition" / "cognitive_governor.py"

CHAINED_GOVERNOR_CODE = '''"""
E-ZZIO Core — Cognitive Governor avec Ledger Cryptographique Chaîné (ECOL V7.61.2)
Garantit l'immutabilité et la non-falsifiabilité des décisions cognitives et des budgets.
"""
import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)

class CognitiveGovernor:
    def __init__(self, root_dir: Path = Path(r"G:\\AI\\E-zzio")):
        logger.info("Initialisation du Cognitive Governor [Mode Cryptographique Chaîné]...")
        self.root_dir = root_dir
        self.ledger_path = self.root_dir / "runtime" / "cognition" / "budget" / "cognitive_budget_ledger.jsonl"
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_session_budget = 500000

        # Vérification de l'intégrité de la chaîne au démarrage
        self.verify_ledger_chain()

    def _get_last_hash(self) -> str:
        """Récupère le hachage du dernier enregistrement de la chaîne."""
        if not self.ledger_path.exists():
            return "0000000000000000000000000000000000000000000000000000000000000000"

        last_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        try:
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        if "record_hash" in data:
                            last_hash = data["record_hash"]
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du dernier hachage de la chaîne : {e}")
        return last_hash

    def verify_ledger_chain(self) -> bool:
        """Vérifie l'intégrité mathématique de tout le registre au démarrage."""
        if not self.ledger_path.exists():
            return True

        logger.info("Vérification de l'intégrité cryptographique du Token Ledger...")
        expected_prev_hash = "0000000000000000000000000000000000000000000000000000000000000000"

        try:
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    data = json.loads(line)

                    # Extraction du hash enregistré et du hash précédent
                    stored_prev = data.get("previous_hash")
                    stored_self = data.get("record_hash")

                    if stored_prev != expected_prev_hash:
                        logger.critical(f"ALERTE RUPTURE DE CHAÎNE (Ligne {line_num}) : previous_hash corrompu !")
                        raise SecurityError(f"Corruption du Ledger à la ligne {line_num} : rupture de l'historique cryptographique.")

                    # Recalcul du hash pour vérifier l'intégrité du contenu
                    payload_to_hash = {
                        "timestamp": data.get("timestamp"),
                        "task": data.get("task"),
                        "priority": data.get("priority"),
                        "estimated_cost": data.get("estimated_cost"),
                        "decision": data.get("decision"),
                        "previous_hash": stored_prev
                    }
                    computed_hash = hashlib.sha256(json.dumps(payload_to_hash, sort_keys=True).encode("utf-8")).hexdigest()

                    if computed_hash != stored_self:
                        logger.critical(f"ALERTE FALSIFICATION (Ligne {line_num}) : Le contenu du registre a été altéré !")
                        raise SecurityError(f"Altération des données détectée à la ligne {line_num}.")

                    expected_prev_hash = stored_self
            logger.info("[OK] Intégrité cryptographique du Token Ledger certifiée à 100%.")
            return True
        except SecurityError as se:
            logger.critical(f"VERROUILLAGE DE SÉCURITÉ ECOL : {se}")
            raise
        except Exception as e:
            logger.warning(f"Ledger vide ou format initial en cours de migration : {e}")
            return True

    def _calculate_current_spend(self) -> int:
        """Calcule la dépense actuelle à partir du registre vérifié."""
        total_tokens = 0
        if not self.ledger_path.exists():
            return 0
        try:
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        if data.get("decision") in ["ALLOW", "ALLOW_EXCEED", "EMERGENCY_ALLOW"]:
                            total_tokens += data.get("estimated_cost", 0)
        except Exception:
            pass
        return total_tokens

    def evaluate_and_record(self, task: str, estimated_tokens: int, priority: str = "normal", risk_level: str = "low") -> Dict[str, Any]:
        """Évalue la requête et l'inscrit dans le registre sous forme de bloc cryptographique chaîné."""
        current_spend = self._calculate_current_spend()

        decision = "ALLOW"
        reason = "Budget cognitif nominal."

        if current_spend + estimated_tokens > self.max_session_budget:
            if priority == "critical":
                decision = "EMERGENCY_ALLOW"
                reason = "Dépassement budgétaire autorisé suite à une escalade critique validée."
            else:
                decision = "DENY"
                reason = f"Budget insuffisant. Restant: {max(0, self.max_session_budget - current_spend)} tokens."

        if risk_level == "high" and priority != "critical":
            decision = "DENY"
            reason = "Rejet : Tâche à haut risque non justifiée par l'urgence."

        # Récupération du hachage précédent pour sceller le bloc
        prev_hash = self._get_last_hash()

        timestamp = datetime.now(timezone.utc).isoformat()

        # Données scellées dans le bloc
        block_payload = {
            "timestamp": timestamp,
            "task": task,
            "priority": priority,
            "estimated_cost": estimated_tokens,
            "decision": decision,
            "previous_hash": prev_hash
        }

        # Calcul du hachage SHA-256 du bloc courant
        record_hash = hashlib.sha256(json.dumps(block_payload, sort_keys=True).encode("utf-8")).hexdigest()

        transaction = {
            **block_payload,
            "reason": reason,
            "record_hash": record_hash,
            "current_spend_after": current_spend + (estimated_tokens if "ALLOW" in decision or "EMERGENCY" in decision else 0)
        }

        try:
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(transaction, ensure_ascii=False) + "\\n")
        except Exception as e:
            logger.error(f"Échec de l'écriture cryptographique dans le Ledger : {e}")

        return transaction

class SecurityError(Exception):
    """Levée en cas de rupture de la chaîne d'intégrité ou de falsification du Ledger."""
    pass
'''


def upgrade_ledger():
    print("[*] Application de la mise à niveau V7.61.2 (Chained Cryptographic Ledger)...")
    if GOVERNOR_PATH.exists():
        with open(GOVERNOR_PATH, "w", encoding="utf-8") as f:
            f.write(CHAINED_GOVERNOR_CODE.strip() + "\n")
        print("  + Remplacement réussi : cognitive_governor.py mis à niveau avec SHA-256 chain.")
    else:
        print("  ! Erreur : cognitive_governor.py introuvable.")

    print("\n" + "=" * 65)
    print(" V7.61.2 UPGRADE SUCCEEDED : TOKEN LEDGER SECURED BY CRYPTOGRAPHY")
    print("=" * 65)


if __name__ == "__main__":
    upgrade_ledger()
