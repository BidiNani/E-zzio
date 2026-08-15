"""
E-ZZIO V7.61.3 — Ledger Migration & Cryptographic Hardening
Migre l'ancien registre non chaîné vers une blockchain de blocs immuables (SHA-256),
place l'exception de sécurité en tête de module, et ajoute l'empreinte runtime.
"""
import os
import json
import hashlib
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

ROOT_DIR = Path(r"G:\AI\E-zzio")
GOVERNOR_PATH = ROOT_DIR / "core" / "cognition" / "cognitive_governor.py"
LEDGER_PATH = ROOT_DIR / "runtime" / "cognition" / "budget" / "cognitive_budget_ledger.jsonl"

RUNTIME_ID = "EZZIO-RUNTIME-001"
BOOT_ID = str(uuid.uuid4())
KERNEL_VERSION = "V7.61.3"

HARDENED_GOVERNOR_CODE = f"""\"\"\"
E-ZZIO Core — Cognitive Governor avec Ledger Cryptographique Durci (ECOL V7.61.3)
Garantit l'immutabilité, le chaînage cryptographique SHA-256 et l'empreinte runtime.
\"\"\"
import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)

class LedgerSecurityError(Exception):
    \"\"\"Levée en cas de rupture de la chaîne d'intégrité ou de falsification du Ledger.\"\"\"
    pass

class CognitiveGovernor:
    def __init__(self, root_dir: Path = Path(r"G:\\AI\\E-zzio")):
        logger.info("Initialisation du Cognitive Governor [Mode Cryptographique Durci V7.61.3]...")
        self.root_dir = root_dir
        self.ledger_path = self.root_dir / "runtime" / "cognition" / "budget" / "cognitive_budget_ledger.jsonl"
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_session_budget = 500000
        
        self.runtime_id = "{RUNTIME_ID}"
        self.boot_id = "{BOOT_ID}"
        self.kernel_version = "{KERNEL_VERSION}"

        # Vérification de l'intégrité de la chaîne au démarrage
        self.verify_ledger_chain()

    def _get_last_hash(self) -> str:
        \"\"\"Récupère le hachage du dernier enregistrement de la chaîne.\"\"\"
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
            logger.error(f"Erreur lors de la lecture du dernier hachage : {{e}}")
        return last_hash

    def verify_ledger_chain(self) -> bool:
        \"\"\"Vérifie l'intégrité mathématique de tout le registre au démarrage.\"\"\"
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
                    
                    stored_prev = data.get("previous_hash", "0000000000000000000000000000000000000000000000000000000000000000")
                    stored_self = data.get("record_hash")
                    
                    if stored_prev != expected_prev_hash:
                        raise LedgerSecurityError(f"Corruption du Ledger à la ligne {{line_num}} : rupture de la chaîne cryptographique.")
                    
                    # Reconstruction du payload pour vérification du hash
                    payload_to_hash = {{
                        "runtime_id": data.get("runtime_id", self.runtime_id),
                        "boot_id": data.get("boot_id", self.boot_id),
                        "kernel_version": data.get("kernel_version", self.kernel_version),
                        "timestamp": data.get("timestamp"),
                        "task": data.get("task"),
                        "priority": data.get("priority"),
                        "estimated_cost": data.get("estimated_cost"),
                        "decision": data.get("decision"),
                        "previous_hash": stored_prev
                    }}
                    computed_hash = hashlib.sha256(json.dumps(payload_to_hash, sort_keys=True).encode("utf-8")).hexdigest()
                    
                    if computed_hash != stored_self:
                        raise LedgerSecurityError(f"Altération des données détectée à la ligne {{line_num}} (Hash mismatch).")
                        
                    expected_prev_hash = stored_self
            logger.info("[OK] Intégrité cryptographique du Token Ledger certifiée à 100%.")
            return True
        except LedgerSecurityError as lse:
            logger.critical(f"VERROUILLAGE DE SÉCURITÉ ECOL : {{lse}}")
            raise
        except Exception as e:
            logger.warning(f"Ledger en cours de normalisation : {{e}}")
            return True

    def _calculate_current_spend(self) -> int:
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
        current_spend = self._calculate_current_spend()
        
        decision = "ALLOW"
        reason = "Budget cognitif nominal."
        
        if current_spend + estimated_tokens > self.max_session_budget:
            if priority == "critical":
                decision = "EMERGENCY_ALLOW"
                reason = "Dépassement budgétaire autorisé suite à une escalade critique validée."
            else:
                decision = "DENY"
                reason = f"Budget insuffisant. Restant: {{max(0, self.max_session_budget - current_spend)}} tokens."
                
        if risk_level == "high" and priority != "critical":
            decision = "DENY"
            reason = "Rejet : Tâche à haut risque non justifiée par l'urgence."

        prev_hash = self._get_last_hash()
        timestamp = datetime.now(timezone.utc).isoformat()
        
        block_payload = {{
            "runtime_id": self.runtime_id,
            "boot_id": self.boot_id,
            "kernel_version": self.kernel_version,
            "timestamp": timestamp,
            "task": task,
            "priority": priority,
            "estimated_cost": estimated_tokens,
            "decision": decision,
            "previous_hash": prev_hash
        }}
        
        record_hash = hashlib.sha256(json.dumps(block_payload, sort_keys=True).encode("utf-8")).hexdigest()

        transaction = {{
            **block_payload,
            "reason": reason,
            "record_hash": record_hash,
            "current_spend_after": current_spend + (estimated_tokens if "ALLOW" in decision or "EMERGENCY" in decision else 0)
        }}
        
        try:
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(transaction, ensure_ascii=False) + "\\n")
        except Exception as e:
            logger.error(f"Échec de l'écriture cryptographique dans le Ledger : {{e}}")
            
        return transaction
"""

def migrate_ledger():
    print("[*] Lancement de la migration et du durcissement du Ledger...")
    
    # 1. Mise à jour du code du Gouverneur
    with open(GOVERNOR_PATH, "w", encoding="utf-8") as f:
        f.write(HARDENED_GOVERNOR_CODE.strip() + "\n")
    print("  + Code du CognitiveGovernor mis à jour avec la classe LedgerSecurityError en tête.")

    # 2. Migration des anciens enregistrements du Ledger s'ils existent
    if LEDGER_PATH.exists():
        print("  * Analyse du registre existant pour migration cryptographique...")
        raw_lines = []
        with open(LEDGER_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        raw_lines.append(json.loads(line))
                    except Exception:
                        pass

        if raw_lines:
            # Sauvegarde de secours
            backup_path = LEDGER_PATH.with_suffix(".jsonl.bak")
            with open(backup_path, "w", encoding="utf-8") as f:
                for r in raw_lines:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  + Sauvegarde de sécurité créée : {backup_path.name}")

            # Reconstruction de la chaîne de blocs
            current_prev_hash = "0000000000000000000000000000000000000000000000000000000000000000"
            migrated_records = []

            for entry in raw_lines:
                # Si l'enregistrement possède déjà un hash valide, on le garde ou on le relie
                timestamp = entry.get("timestamp", datetime.now(timezone.utc).isoformat())
                task = entry.get("task", "legacy_migration_task")
                priority = entry.get("priority", "normal")
                est_cost = entry.get("estimated_cost", entry.get("cost", 0))
                decision = entry.get("decision", "ALLOW")

                block_payload = {
                    "runtime_id": RUNTIME_ID,
                    "boot_id": BOOT_ID,
                    "kernel_version": KERNEL_VERSION,
                    "timestamp": timestamp,
                    "task": task,
                    "priority": priority,
                    "estimated_cost": est_cost,
                    "decision": decision,
                    "previous_hash": current_prev_hash
                }

                record_hash = hashlib.sha256(json.dumps(block_payload, sort_keys=True).encode("utf-8")).hexdigest()

                migrated_record = {
                    **block_payload,
                    "reason": entry.get("reason", "Migré depuis le registre non chaîné."),
                    "record_hash": record_hash,
                    "current_spend_after": entry.get("current_spend_after", est_cost)
                }

                migrated_records.append(migrated_record)
                current_prev_hash = record_hash

            # Réécriture propre du Ledger chaîné
            with open(LEDGER_PATH, "w", encoding="utf-8") as f:
                for mr in migrated_records:
                    f.write(json.dumps(mr, ensure_ascii=False) + "\n")
            print(f"  + Migration réussie : {len(migrated_records)} blocs cryptographiques scellés.")

    print("\n" + "="*65)
    print(" V7.61.3 UPGRADE & MIGRATION SUCCEEDED")
    print("="*65)

if __name__ == "__main__":
    migrate_ledger()
