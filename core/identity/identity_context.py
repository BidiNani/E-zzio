"""
E-ZZIO V7.31 — Immutable Identity Context
Représente l'objet d'identité scellé et gelé généré au boot.
"""

import os
import hashlib
import hmac
import uuid
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = ROOT_DIR / "config"
RUNTIME_IDENTITY_DIR = ROOT_DIR / "runtime" / "identity"
ENV_PATH = ROOT_DIR / "secrets" / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=True)


class ImmutableIdentityContext:
    def __init__(self):
        secret = os.getenv("EZZIO_LEDGER_SECRET")
        if not secret:
            raise ValueError("CRITICAL_SECURITY_ERROR: EZZIO_LEDGER_SECRET is required.")
        self.secret_key = secret.encode("utf-8")

        self._boot_session_id = f"sess-{uuid.uuid4().hex[:12]}"
        self._boot_timestamp = datetime.now(timezone.utc).isoformat()

        self._constitution_hash = self._hash_file(CONFIG_DIR / "constitution.json")
        self._persona_hash = self._hash_file(CONFIG_DIR / "persona.json")
        self._lore_hash = self._hash_file(CONFIG_DIR / "lore.md")
        self._skill_manifest_hash = self._hash_file(CONFIG_DIR / "skills_manifest.json")
        self._memory_anchor_hash = self._hash_file(CONFIG_DIR / "memory_graph.json")
        self._identity_spec_hash = self._hash_file(RUNTIME_IDENTITY_DIR / "identity.json")

        combined = (
            self._constitution_hash
            + self._persona_hash
            + self._lore_hash
            + self._skill_manifest_hash
            + self._memory_anchor_hash
            + self._identity_spec_hash
        )
        self._identity_root_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()
        self._signature = hmac.new(self.secret_key, self._identity_root_hash.encode("utf-8"), hashlib.sha256).hexdigest()

    def _hash_file(self, path: Path) -> str:
        if not path.exists():
            return hashlib.sha256(b"EMPTY").hexdigest()
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @property
    def boot_session_id(self) -> str:
        return self._boot_session_id

    @property
    def boot_timestamp(self) -> str:
        return self._boot_timestamp

    @property
    def constitution_hash(self) -> str:
        return self._constitution_hash

    @property
    def persona_hash(self) -> str:
        return self._persona_hash

    @property
    def lore_hash(self) -> str:
        return self._lore_hash

    @property
    def skill_manifest_hash(self) -> str:
        return self._skill_manifest_hash

    @property
    def memory_anchor_hash(self) -> str:
        return self._memory_anchor_hash

    @property
    def identity_root_hash(self) -> str:
        return self._identity_root_hash

    @property
    def signature(self) -> str:
        return self._signature

    def to_dict(self) -> dict:
        return {
            "boot_session_id": self._boot_session_id,
            "boot_timestamp": self._boot_timestamp,
            "constitution_hash": self._constitution_hash,
            "persona_hash": self._persona_hash,
            "lore_hash": self._lore_hash,
            "skill_manifest_hash": self._skill_manifest_hash,
            "memory_anchor_hash": self._memory_anchor_hash,
            "identity_root_hash": self._identity_root_hash,
            "signature": self._signature,
        }
