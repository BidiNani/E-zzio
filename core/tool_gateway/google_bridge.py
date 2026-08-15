"""
E-ZZIO V7.40 — Google Identity Bridge & Secure Vault
Gère le stockage chiffré et scellé des tokens OAuth2 sans polluer l'identité racine.
"""
import os
import json
import base64
import hashlib
import hmac
from contracts.config_port import IConfigProvider
from pathlib import Path
from datetime import datetime, timezone
from cryptography.fernet import Fernet

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
VAULT_FILE = ROOT_DIR / "runtime" / "vault" / "google_oauth.vault"
class GoogleIdentityBridge:
    def __init__(self, config: IConfigProvider = None):
        if config is None:
            from runtime.adapters.config.dotenv_provider import DotEnvConfigProvider
            config = DotEnvConfigProvider()
        secret = config.require("EZZIO_LEDGER_SECRET")
        self.master_secret = secret.encode("utf-8")
        
        # Dérivation d'une clé AES/Fernet 32-bytes URL-safe à partir du secret maître
        key_material = hashlib.sha256(self.master_secret).digest()
        self.cipher = Fernet(base64.urlsafe_b64encode(key_material))
        
        VAULT_FILE.parent.mkdir(parents=True, exist_ok=True)

    def store_tokens(self, access_token: str, refresh_token: str, scopes: list, expires_in_sec: int) -> bool:
        """Chiffre et scelle les tokens dans le Vault."""
        payload = {
            "provider": "google",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "scopes": scopes,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "expires_in": expires_in_sec
        }
        
        raw_json = json.dumps(payload).encode("utf-8")
        encrypted_payload = self.cipher.encrypt(raw_json)
        
        # Sceau HMAC sur la donnée chiffrée
        signature = hmac.new(self.master_secret, encrypted_payload, hashlib.sha256).hexdigest()
        
        vault_data = {
            "encrypted_data": encrypted_payload.decode("utf-8"),
            "hmac_signature": signature
        }
        
        VAULT_FILE.write_text(json.dumps(vault_data, indent=2), encoding="utf-8")
        return True

    def retrieve_tokens(self) -> dict:
        """Vérifie le sceau, déchiffre et retourne les tokens."""
        if not VAULT_FILE.exists():
            return {"valid": False, "error": "VAULT_NOT_FOUND"}
            
        try:
            vault_data = json.loads(VAULT_FILE.read_text(encoding="utf-8"))
            encrypted_payload = vault_data["encrypted_data"].encode("utf-8")
            stored_sig = vault_data["hmac_signature"]
            
            # Vérification de l'intégrité (Anti-Tampering)
            calc_sig = hmac.new(self.master_secret, encrypted_payload, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(calc_sig, stored_sig):
                return {"valid": False, "error": "VAULT_CORRUPTED_OR_TAMPERED"}
                
            # Déchiffrement
            raw_json = self.cipher.decrypt(encrypted_payload).decode("utf-8")
            payload = json.loads(raw_json)
            
            return {"valid": True, "tokens": payload, "error": None}
            
        except Exception as e:
            return {"valid": False, "error": f"VAULT_DECRYPTION_FAILED: {str(e)}"}


# Instance globale de rétrocompatibilité pour les modules non encore migrés
google_bridge = GoogleIdentityBridge()

