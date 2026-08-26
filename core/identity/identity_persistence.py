"""
E-ZZIO V7.31 — Identity Persistence Layer
Gère le chargement, le hachage et le scellement de la spécification d'identité.
"""

import os
import hashlib
import hmac
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = ROOT_DIR / "config"
RUNTIME_IDENTITY_DIR = ROOT_DIR / "runtime" / "identity"
ENV_PATH = ROOT_DIR / "secrets" / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=True)


class IdentityPersistenceEngine:
    def __init__(self):
        secret = os.getenv("EZZIO_LEDGER_SECRET")
        if not secret:
            raise ValueError("CRITICAL_SECURITY_ERROR: EZZIO_LEDGER_SECRET is required.")
        self.secret_key = secret.encode("utf-8")
        RUNTIME_IDENTITY_DIR.mkdir(parents=True, exist_ok=True)

    def _hash_file(self, path: Path) -> str:
        if not path.exists():
            return hashlib.sha256(b"EMPTY").hexdigest()
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def build_and_seal_identity_persistence(self) -> dict:
        const_hash = self._hash_file(CONFIG_DIR / "constitution.json")
        persona_hash = self._hash_file(CONFIG_DIR / "persona.json")
        lore_hash = self._hash_file(CONFIG_DIR / "lore.md")
        identity_spec_hash = self._hash_file(RUNTIME_IDENTITY_DIR / "identity.json")

        (RUNTIME_IDENTITY_DIR / "constitution.hash").write_text(const_hash, encoding="utf-8")
        (RUNTIME_IDENTITY_DIR / "persona.hash").write_text(persona_hash, encoding="utf-8")
        (RUNTIME_IDENTITY_DIR / "lore.hash").write_text(lore_hash, encoding="utf-8")

        combined = const_hash + persona_hash + lore_hash + identity_spec_hash
        identity_root_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()
        (RUNTIME_IDENTITY_DIR / "identity_root.hash").write_text(identity_root_hash, encoding="utf-8")

        signature = hmac.new(self.secret_key, identity_root_hash.encode("utf-8"), hashlib.sha256).hexdigest()
        (RUNTIME_IDENTITY_DIR / "identity_signature.sig").write_text(signature, encoding="utf-8")

        return {
            "constitution_hash": const_hash,
            "persona_hash": persona_hash,
            "lore_hash": lore_hash,
            "identity_spec_hash": identity_spec_hash,
            "identity_root_hash": identity_root_hash,
            "signature": signature,
        }


identity_persistence = IdentityPersistenceEngine()
