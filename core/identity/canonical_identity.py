"""
E-ZZIO V7.28.10 — Canonical Identity
La source unique de vérité pour l'identité du système.
"""
import json
from pathlib import Path

# Référence unique au propriétaire (Point de vérité unique)
OWNER_PROFILE = "Enrik"

class CanonicalIdentity:
    def __init__(self):
        self.data = {
            "name": "E-ZZIO",
            "version": "V7.28.10",
            "owner": OWNER_PROFILE,
            "identity": {
                "type": "local_ai_companion",
                "mission": "Orchestration décisionnelle haute disponibilité et résilience cryptographique."
            },
            "policy": {
                "allow_gpu": True,
                "fail_closed_on_integrity_error": True,
                "forensic_logging": True
            },
            "manifest": {
                "modules": ["ledger", "recovery", "archive", "identity"],
                "skills": ["router", "integrity_checker"]
            }
        }

    def get_payload(self) -> dict:
        return self.data

    def get_canonical_json(self) -> str:
        # Sort keys est CRUCIAL pour le hashing déterministe
        return json.dumps(self.data, sort_keys=True, ensure_ascii=False)
