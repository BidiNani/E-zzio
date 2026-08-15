"""
E-ZZIO V7.29.3 — Identity Validator
Vérifie la validité des ancres enregistrées dans runtime/identity/.
"""
import os
import json
import hashlib
import hmac
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RUNTIME_IDENTITY_DIR = ROOT_DIR / "runtime" / "identity"
ENV_PATH = ROOT_DIR / "secrets" / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=True)

class IdentityValidator:
    @staticmethod
    def validate_persistence_seals() -> dict:
        spec_path = RUNTIME_IDENTITY_DIR / "identity.json"
        root_hash_path = RUNTIME_IDENTITY_DIR / "identity_root.hash"
        sig_path = RUNTIME_IDENTITY_DIR / "identity_signature.sig"

        if not spec_path.exists() or not root_hash_path.exists() or not sig_path.exists():
            return {"valid": False, "error": "MISSING_IDENTITY_PERSISTENCE_FILES"}

        secret_key = os.getenv("EZZIO_LEDGER_SECRET", "default_secret").encode("utf-8")
        stored_root = root_hash_path.read_text(encoding="utf-8").strip()
        stored_sig = sig_path.read_text(encoding="utf-8").strip()

        calculated_sig = hmac.new(secret_key, stored_root.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calculated_sig, stored_sig):
            return {"valid": False, "error": "INVALID_IDENTITY_HMAC_SIGNATURE"}

        return {"valid": True, "identity_root": stored_root, "error": None}

identity_validator = IdentityValidator()
