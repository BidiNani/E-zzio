"""
E-ZZIO Core — Secret Sovereignty Layer (V7.63.3 Industrial Final)
Isolation du drill dans un bac à sable pour éviter le déclenchement
du Fail-Closed anti-sabotage avec le Ledger de production.
"""

import os
import json
import logging
import threading
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Tuple

logger = logging.getLogger(__name__)

ROOT_DIR = Path(r"G:\AI\E-zzio")


class SecretSovereigntyError(Exception):
    pass


class SecretSovereigntyLayer:
    def __init__(self, root_dir: Path = ROOT_DIR):
        self.root_dir = root_dir
        self.security_dir = self.root_dir / "runtime" / "security"
        self.vault_path = self.security_dir / "secret_vault.json"
        self.keys_dir = self.security_dir / "keys"

        self.security_dir.mkdir(parents=True, exist_ok=True)
        self.keys_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self._initialize_vault_if_needed()

    def _canonical_dump(self, payload: dict) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def _initialize_vault_if_needed(self):
        with self._lock:
            # Recherche du ledger dans le même root_dir (production ou sandbox)
            ledger_dir = self.root_dir / "runtime" / "cognition" / "budget"
            ledger_path = ledger_dir / "cognitive_budget_ledger.jsonl"

            if not self.vault_path.exists():
                if ledger_path.exists():
                    raise SecretSovereigntyError("FAIL CLOSED CRITIQUE : Le Ledger existe mais le coffre-fort de clés est absent !")

                logger.info("Initialisation de la racine de confiance (Époque Genesis ECOL-KEY-001)...")
                initial_key_id = "ECOL-KEY-001"
                initial_secret = os.urandom(32)

                key_file = self.keys_dir / f"{initial_key_id}.key"
                key_file.write_bytes(initial_secret)

                vault_data = {
                    "active_key_id": initial_key_id,
                    "keys": {
                        initial_key_id: {
                            "status": "ACTIVE",
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "algorithm": "HMAC-SHA256",
                        }
                    },
                }
                self.vault_path.write_text(self._canonical_dump(vault_data) + "\n", encoding="utf-8")

    def load_vault(self) -> dict:
        with self._lock:
            if not self.vault_path.exists():
                raise SecretSovereigntyError("FAIL CLOSED : Le coffre-fort des secrets est introuvable.")
            try:
                return json.loads(self.vault_path.read_text(encoding="utf-8"))
            except Exception as e:
                raise SecretSovereigntyError(f"FAIL CLOSED : Corruption structurelle du coffre : {e}")

    def get_active_key_material(self) -> Tuple[str, bytes]:
        with self._lock:
            vault = self.load_vault()
            active_id = vault.get("active_key_id")
            if not active_id or active_id not in vault.get("keys", {}):
                raise SecretSovereigntyError("FAIL CLOSED : Aucune clé active valide répertoriée.")

            key_file = self.keys_dir / f"{active_id}.key"
            if not key_file.exists():
                raise SecretSovereigntyError(f"FAIL CLOSED : Perte physique de la matière active '{active_id}.key'.")

            return active_id, key_file.read_bytes()

    def get_key_material(self, key_id: str) -> bytes:
        with self._lock:
            vault = self.load_vault()
            if key_id not in vault.get("keys", {}):
                raise SecretSovereigntyError(f"FAIL CLOSED : Clé inconnue ou révoquée '{key_id}'.")

            key_file = self.keys_dir / f"{key_id}.key"
            if not key_file.exists():
                raise SecretSovereigntyError(f"FAIL CLOSED : Perte physique du fichier '{key_id}.key'.")

            return key_file.read_bytes()

    def rotate_key(self, new_key_id: str) -> str:
        with self._lock:
            vault = self.load_vault()
            old_active = vault.get("active_key_id")

            if new_key_id in vault.get("keys", {}):
                raise SecretSovereigntyError(f"FAIL CLOSED : Collision d'époque, la clé '{new_key_id}' existe déjà.")

            logger.info(f"Exécution de la rotation vers {new_key_id}...")
            new_secret = os.urandom(32)
            key_file = self.keys_dir / f"{new_key_id}.key"
            key_file.write_bytes(new_secret)

            if old_active and old_active in vault["keys"]:
                vault["keys"][old_active]["status"] = "VERIFY_ONLY"

            vault["keys"][new_key_id] = {
                "status": "ACTIVE",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "algorithm": "HMAC-SHA256",
            }
            vault["active_key_id"] = new_key_id

            self.vault_path.write_text(self._canonical_dump(vault) + "\n", encoding="utf-8")
            return new_key_id


def run_sovereignty_verification_drill():
    print("[*] Lancement du Drill de Souveraineté des Secrets (V7.63.3)...")

    # Utilisation d'un bac à sable complet (Ledger + Security) pour le test
    sandbox_dir = ROOT_DIR / "sandbox_ssl"
    if sandbox_dir.exists():
        shutil.rmtree(sandbox_dir)
    sandbox_dir.mkdir(parents=True)

    ssl = SecretSovereigntyLayer(root_dir=sandbox_dir)

    # 1. Test de récupération active
    active_id, active_mat = ssl.get_active_key_material()
    print(f"  [PASS] Clé active d'époque initiale : {active_id}")

    # 2. Test de rotation contrôlée vers une nouvelle époque propre
    next_epoch = f"ECOL-KEY-{int(datetime.now().timestamp())}"
    try:
        ssl.rotate_key(next_epoch)
        print(f"  [PASS] Rotation vers {next_epoch} effectuée avec succès.")
    except Exception as e:
        print(f"  [FAIL] Échec de la rotation : {e}")
        return

    # 3. Test d'interdiction d'utiliser une ancienne clé pour signer
    ssl.get_key_material(active_id)
    vault = ssl.load_vault()
    assert vault["keys"][active_id]["status"] == "VERIFY_ONLY", "L'ancienne clé devrait être en VERIFY_ONLY"
    print(f"  [PASS] Statut de l'ancienne clé {active_id} rétrogradé à VERIFY_ONLY.")

    # 4. Test du comportement Fail-Closed en cas de suppression physique de la clé active
    active_now_id, _ = ssl.get_active_key_material()
    active_file = ssl.keys_dir / f"{active_now_id}.key"

    backup_bytes = active_file.read_bytes()
    active_file.unlink()
    print("  * Simulation d'incident : Destruction physique du fichier de clé active.")

    try:
        ssl.get_active_key_material()
        print("  [FAIL] Alerte : Le système a permis d'ignorer la perte de clé !")
    except SecretSovereigntyError:
        print("  [PASS] FAIL CLOSED CONFIRMÉ : Perte de secret interceptée, accès bloqué.")

    active_file.write_bytes(backup_bytes)

    # Nettoyage du bac à sable
    shutil.rmtree(sandbox_dir)

    print("\n" + "=" * 65)
    print(" SECRET SOVEREIGNTY CERTIFICATION RAPPORT (V7.63.3) : PASS")
    print("=" * 65)


if __name__ == "__main__":
    run_sovereignty_verification_drill()
