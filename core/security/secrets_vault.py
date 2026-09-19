"""
E-ZZIO Security — Secrets Vault & At-Rest Encryption (age / AES-256-GCM / DPAPI).
Permet de chiffrer secrets/.env et les identifiants sensibles au repos sur le disque :
1. Provisionnement sécurisé de la clé maître :
   - Variable d'environnement système (EZZIO_VAULT_PASSPHRASE / EZZIO_MASTER_KEY)
   - Trousseau OS natif Windows DPAPI (CryptProtectData / CryptUnprotectData)
   - Saisie explicite en paramètre (CLI interactive)
2. Chiffrement AES-256-GCM avec dérivation de clé PBKDF2-HMAC-SHA256 (100 000 itérations)
3. Déchiffrement direct en mémoire vive (zéro secret en clair sur disque)
4. Intégrité vérifiée par tag d'authentification GCM
"""
from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

logger = logging.getLogger("SecretsVault")


# Structures DPAPI pour Windows
class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.c_ulong),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte))
    ]


class SecretsVault:
    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root).resolve()
        self.secrets_dir = self.workspace_root / "secrets"
        self.secrets_dir.mkdir(parents=True, exist_ok=True)

    def get_passphrase(self, explicit_passphrase: str | None = None) -> str | None:
        """
        Récupère la clé maître dans l'ordre de priorité sécurisé :
        1. Paramètre explicite (CLI / Appel direct)
        2. Variable d'environnement système (EZZIO_VAULT_PASSPHRASE / EZZIO_MASTER_KEY)
        3. Fichier scellé par DPAPI Windows (secrets/.vault_dpapi.bin)
        """
        if explicit_passphrase:
            return explicit_passphrase

        # 1. Variable d'environnement injectée au runtime
        env_key = os.environ.get("EZZIO_VAULT_PASSPHRASE") or os.environ.get("EZZIO_MASTER_KEY")
        if env_key:
            return env_key

        # 2. Clé scellée DPAPI locale
        dpapi_file = self.secrets_dir / ".vault_dpapi.bin"
        if dpapi_file.exists():
            unsealed = self.unseal_from_dpapi(dpapi_file)
            if unsealed:
                return unsealed

        return None

    def seal_to_dpapi(self, passphrase: str, dest_file: Path | str | None = None) -> bool:
        """Scelle la clé maître avec la DPAPI Windows (clé liée au compte utilisateur Windows)."""
        if sys.platform != "win32":
            return False

        dst = Path(dest_file or (self.secrets_dir / ".vault_dpapi.bin")).resolve()
        try:
            data = passphrase.encode("utf-8")
            blob_in = DATA_BLOB(len(data), ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_ubyte)))
            blob_out = DATA_BLOB()

            res = ctypes.windll.crypt32.CryptProtectData(
                ctypes.byref(blob_in),
                "EZZIO_MASTER_VAULT_KEY",
                None,
                None,
                None,
                0,
                ctypes.byref(blob_out)
            )
            if res:
                enc_bytes = ctypes.string_at(blob_out.pbData, blob_out.cbData)
                ctypes.windll.kernel32.LocalFree(blob_out.pbData)
                dst.write_bytes(enc_bytes)
                return True
            return False
        except Exception as exc:
            logger.error("[VAULT-DPAPI-ERROR] Échec de scellement DPAPI : %s", exc)
            return False

    def unseal_from_dpapi(self, src_file: Path | str | None = None) -> str | None:
        """Descellera la clé maître depuis la DPAPI Windows."""
        if sys.platform != "win32":
            return None

        src = Path(src_file or (self.secrets_dir / ".vault_dpapi.bin")).resolve()
        if not src.exists():
            return None

        try:
            data = src.read_bytes()
            blob_in = DATA_BLOB(len(data), ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_ubyte)))
            blob_out = DATA_BLOB()

            res = ctypes.windll.crypt32.CryptUnprotectData(
                ctypes.byref(blob_in),
                None,
                None,
                None,
                None,
                0,
                ctypes.byref(blob_out)
            )
            if res:
                plain_bytes = ctypes.string_at(blob_out.pbData, blob_out.cbData)
                ctypes.windll.kernel32.LocalFree(blob_out.pbData)
                return plain_bytes.decode("utf-8")
            return None
        except Exception as exc:
            logger.warning("[VAULT-DPAPI-WARN] Échec de descellement DPAPI : %s", exc)
            return None

    def _derive_key(self, passphrase: str, salt: bytes) -> bytes:
        """Dérive une clé AES de 256 bits via PBKDF2-HMAC-SHA256."""
        if HAS_CRYPTOGRAPHY:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100_000,
            )
            return kdf.derive(passphrase.encode("utf-8"))
        else:
            return hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, 100_000, dklen=32)

    def encrypt_env(
        self,
        source_file: str | Path,
        dest_file: str | Path,
        passphrase: str | None = None
    ) -> dict[str, Any]:
        """Chiffre un fichier .env vers un conteneur sécurisé .env.enc."""
        resolved_pass = self.get_passphrase(passphrase)
        if not resolved_pass:
            return {
                "ok": False,
                "error": "Aucune clé maître disponible (définir EZZIO_VAULT_PASSPHRASE ou initialiser DPAPI)."
            }

        src = Path(source_file).resolve()
        dst = Path(dest_file).resolve()

        if not src.exists():
            return {"ok": False, "error": f"Fichier source introuvable : {src}"}

        raw_bytes = src.read_bytes()
        salt = os.urandom(16)
        nonce = os.urandom(12)
        key = self._derive_key(resolved_pass, salt)

        if HAS_CRYPTOGRAPHY:
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(nonce, raw_bytes, None)
        else:
            import hmac
            keystream = hashlib.sha256(key + nonce).digest()
            while len(keystream) < len(raw_bytes):
                keystream += hashlib.sha256(keystream).digest()
            encrypted_data = bytes(b ^ k for b, k in zip(raw_bytes, keystream[:len(raw_bytes)], strict=False))
            tag = hmac.new(key, nonce + encrypted_data, hashlib.sha256).digest()
            ciphertext = encrypted_data + tag

        envelope = {
            "version": "2.0",
            "algorithm": "AES-256-GCM" if HAS_CRYPTOGRAPHY else "PBKDF2-XOR-HMAC",
            "salt_b64": base64.b64encode(salt).decode("ascii"),
            "nonce_b64": base64.b64encode(nonce).decode("ascii"),
            "data_b64": base64.b64encode(ciphertext).decode("ascii"),
        }

        dst.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
        return {
            "ok": True,
            "dest_file": str(dst),
            "bytes_encrypted": len(raw_bytes),
            "key_source": "explicit" if passphrase else ("env" if os.environ.get("EZZIO_VAULT_PASSPHRASE") else "dpapi")
        }

    def decrypt_to_memory(
        self,
        encrypted_file: str | Path,
        passphrase: str | None = None
    ) -> dict[str, Any]:
        """Déchiffre un conteneur directement en mémoire vive sans écriture disque."""
        resolved_pass = self.get_passphrase(passphrase)
        if not resolved_pass:
            return {
                "ok": False,
                "error": "Aucune clé maître disponible (définir EZZIO_VAULT_PASSPHRASE ou initialiser DPAPI)."
            }

        dst = Path(encrypted_file).resolve()
        if not dst.exists():
            return {"ok": False, "error": f"Conteneur chiffré introuvable : {dst}"}

        try:
            envelope = json.loads(dst.read_text(encoding="utf-8"))
            salt = base64.b64decode(envelope["salt_b64"])
            nonce = base64.b64decode(envelope["nonce_b64"])
            ciphertext = base64.b64decode(envelope["data_b64"])
            key = self._derive_key(resolved_pass, salt)

            if HAS_CRYPTOGRAPHY and envelope.get("algorithm") == "AES-256-GCM":
                aesgcm = AESGCM(key)
                plain_bytes = aesgcm.decrypt(nonce, ciphertext, None)
            else:
                import hmac
                tag = ciphertext[-32:]
                encrypted_data = ciphertext[:-32]
                computed_tag = hmac.new(key, nonce + encrypted_data, hashlib.sha256).digest()
                if not hmac.compare_digest(tag, computed_tag):
                    return {"ok": False, "error": "[INTEGRITY ERROR] Mot de passe incorrect ou données altérées."}
                keystream = hashlib.sha256(key + nonce).digest()
                while len(keystream) < len(encrypted_data):
                    keystream += hashlib.sha256(keystream).digest()
                plain_bytes = bytes(b ^ k for b, k in zip(encrypted_data, keystream[:len(encrypted_data)], strict=False))

            lines = plain_bytes.decode("utf-8").splitlines()
            env_vars: dict[str, str] = {}
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip().strip("\"'")

            return {"ok": True, "env_vars": env_vars, "keys_count": len(env_vars)}

        except Exception as exc:
            return {"ok": False, "error": f"Échec de déchiffrement : {exc}"}


# Singleton global
secrets_vault = SecretsVault()
