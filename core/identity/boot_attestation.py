"""
E-ZZIO V7.31 — Boot Attestation Engine
Génère la preuve d'attestation au démarrage (boot_attestation.json).
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from core.identity.identity_chain_validator import identity_chain_validator
from core.identity.identity_context import ImmutableIdentityContext
from core.identity.identity_guardian import IdentityGuardian

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ATTESTATION_FILE = ROOT_DIR / "runtime" / "identity" / "boot_attestation.json"


class BootAttestationEngine:
    @staticmethod
    def generate_attestation(context: ImmutableIdentityContext, guardian: IdentityGuardian) -> dict:
        ATTESTATION_FILE.parent.mkdir(parents=True, exist_ok=True)

        audit_res = guardian.audit_now()
        chain_res = identity_chain_validator.validate_chain()

        attestation = {
            "boot_session_id": context.boot_session_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "identity_root_hash": context.identity_root_hash,
            "signature": context.signature,
            "guardian_status": audit_res.get("state"),
            "chain_status": "VERIFIED" if chain_res.get("valid") else "FAILED",
            "chain_block_count": chain_res.get("block_count", 0),
            "attestation_status": "CERTIFIED_10_10" if audit_res.get("valid") and chain_res.get("valid") else "REJECTED",
        }

        ATTESTATION_FILE.write_text(json.dumps(attestation, indent=2), encoding="utf-8")
        return attestation


boot_attestation_engine = BootAttestationEngine()
