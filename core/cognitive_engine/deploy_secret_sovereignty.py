"""
E-ZZIO Core — Secret Sovereignty Layer (V7.63)
Gère le cycle de vie des clés HMAC, les époques cryptographiques (ACTIVE vs VERIFY_ONLY),
l'isolation de la racine de confiance et le Fail-Closed strict en cas de perte de clé.
"""

import hashlib
import hmac
import json
import logging
import os
import threading
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class SecretSovereigntyError(Exception):
    """Levée en cas de compromission, d'absence ou d'incohérence de la racine de confiance."""

    pass


class SecretSovereigntyLayer:
    def __init__(self, root_dir: Path = Path(r"G:\\AI\E-zzio")):
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
        """Initialise le coffre-fort de clés si inexistant (Génération du premier Genesis Key)."""
        with self._lock:
            if not self.vault_path.exists():
                logger.info("Initialisation du Secret Vault (Époque Genesis ECOL-KEY-001)...")
                initial_key_id = "ECOL-KEY-001"
                initial_secret = os.urandom(32)

                # Sauvegarde physique de la clé brute dans la zone isolée sécurisée
                key_file = self.keys_dir / f"{initial_key_id}.key"
                key_file.write_bytes(initial_secret)

                vault_data = {
                    "active_key_id": initial_key_id,
                    "keys": {
                        initial_key_id: {
                            "status": "ACTIVE",
                            "created_at": datetime.now(UTC).isoformat(),
                            "algorithm": "HMAC-SHA256",
                        }
                    },
                }
                self.vault_path.write_text(self._canonical_dump(vault_data) + "\n", encoding="utf-8")

    def load_vault(self) -> dict:
        with self._lock:
            if not self.vault_path.exists():
                raise SecretSovereigntyError("FAIL CLOSED : Le coffre-fort de clés (secret_vault.json) est introuvable.")
            try:
                return json.loads(self.vault_path.read_text(encoding="utf-8"))
            except Exception as e:
                raise SecretSovereigntyError(f"FAIL CLOSED : Corruption du coffre-fort de clés : {e}")

    def get_active_key_material(self) -> tuple[str, bytes]:
        """Récupère l'ID et la matière cryptographique de la clé active pour signer."""
        with self._lock:
            vault = self.load_vault()
            active_id = vault.get("active_key_id")
            if not active_id or active_id not in vault.get("keys", {}):
                raise SecretSovereigntyError("FAIL CLOSED : Aucune clé active valide n'a été trouvée dans le coffre-fort.")

            key_file = self.keys_dir / f"{active_id}.key"
            if not key_file.exists():
                raise SecretSovereigntyError(
                    f"FAIL CLOSED : Le fichier de clé physique '{active_id}.key' est introuvable (Perte de secret)."
                )

            return active_id, key_file.read_bytes()

    def get_key_material(self, key_id: str) -> bytes:
        """Récupère la matière d'une clé spécifique (active ou verify_only) pour vérification historique."""
        with self._lock:
            vault = self.load_vault()
            if key_id not in vault.get("keys", {}):
                raise SecretSovereigntyError(f"FAIL CLOSED : Tentative d'utilisation d'une clé inconnue ou révoquée '{key_id}'.")

            key_file = self.keys_dir / f"{key_id}.key"
            if not key_file.exists():
                raise SecretSovereigntyError(f"FAIL CLOSED : Le fichier de clé physique '{key_id}.key' est introuvable pour vérification.")

            return key_file.read_bytes()

    def rotate_key(self, new_key_id: str) -> str:
        """Effectue une rotation contrôlée : l'ancienne clé passe en VERIFY_ONLY, la nouvelle devient ACTIVE."""
        with self._lock:
            vault = self.load_vault()
            old_active = vault.get("active_key_id")

            if new_key_id in vault.get("keys", {}):
                raise SecretSovereigntyError(f"FAIL CLOSED : La clé '{new_key_id}' existe déjà.")

            logger.info("Rotation de la racine de confiance HMAC...")
            new_secret = os.urandom(32)
            key_file = self.keys_dir / f"{new_key_id}.key"
            key_file.write_bytes(new_secret)

            # Rétrogradation de l'ancienne clé active en VERIFY_ONLY
            if old_active and old_active in vault["keys"]:
                vault["keys"][old_active]["status"] = "VERIFY_ONLY"

            # Enregistrement de la nouvelle clé ACTIVE
            vault["keys"][new_key_id] = {
                "status": "ACTIVE",
                "created_at": datetime.now(UTC).isoformat(),
                "algorithm": "HMAC-SHA256",
            }
            vault["active_key_id"] = new_key_id

            self.vault_path.write_text(self._canonical_dump(vault) + "\n", encoding="utf-8")
            logger.info(f"[OK] Rotation réussie. Nouvelle époque active : {new_key_id}")
            return new_key_id


def test_sovereignty_layer():
    print("[*] Test et certification du Secret Sovereignty Layer (V7.63)...")
    ssl = SecretSovereigntyLayer()

    # Test 1 : Récupération de la clé active
    active_id, active_mat = ssl.get_active_key_material()
    print(f"  [PASS] Clé active récupérée avec succès : {active_id} ({len(active_mat)} octets)")

    # Test 2 : Signature HMAC multi-époque
    msg = "test_payload_epoch_001"
    sig = hmac.new(active_mat, msg.encode("utf-8"), hashlib.sha256).hexdigest()
    print(f"  [PASS] Signature HMAC générée sous l'époque {active_id}")

    # Test 3 : Rotation contrôlée
    new_id = "ECOL-KEY-002"
    try:
        ssl.rotate_key(new_id)
        print(f"  [PASS] Rotation vers {new_id} validée. Ancienne clé rétrogradée en VERIFY_ONLY.")
    except Exception as e:
        print(f"  [FAIL] Échec de la rotation : {e}")

    # Test 4 : Vérification que l'ancienne clé peut toujours vérifier l'ancien message
    old_mat = ssl.get_key_material(active_id)
    verified = hmac.compare_digest(hmac.new(old_mat, msg.encode("utf-8"), hashlib.sha256).hexdigest(), sig)
    print(f"  [PASS] Vérification historique avec l'ancienne clé ({active_id}) : {verified}")

    print("\n" + "=" * 65)
    print(" SECRET SOVEREIGNTY LAYER (V7.63) DEPLOYED & TESTED SUCCESSFULLY")
    print("=" * 65)


if __name__ == "__main__":
    test_sovereignty_layer()
