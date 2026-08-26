"""
E-ZZIO V9.2.3 — Manifest Validator
Vérifie la conformité structurelle de tout manifeste externe.
Redirige vers la zone de quarantaine en cas d'échec.
"""

import json
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(r"G:\AI\E-zzio")
QUARANTINE_DIR = ROOT_DIR / "runtime" / "capabilities" / "quarantine"


class ManifestValidator:
    def __init__(self):
        QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

    def validate_and_inspect(self, manifest: dict) -> dict:
        required_fields = ["capability_id", "version", "origin", "behavior", "resource_budget", "rollback"]

        # 1. Vérification structurelle
        for field in required_fields:
            if field not in manifest:
                reason = f"Champ obligatoire manquant dans le manifeste : '{field}'"
                self._send_to_quarantine(manifest, reason)
                return {"status": "REJECTED", "reason": reason}

        # 2. Vérification des ressources matérielles (Règle HW-001)
        resources = manifest.get("resource_budget", {})
        if resources.get("gpu_allowed", False):
            reason = "Violation critique HW-001 : Utilisation du GPU local non autorisée."
            self._send_to_quarantine(manifest, reason)
            return {"status": "REJECTED", "reason": reason}

        return {"status": "VALIDATED", "reason": "Manifeste conforme aux exigences immunitaires."}

    def _send_to_quarantine(self, manifest: dict, reason: str):
        cap_id = manifest.get("capability_id", "UNKNOWN_CORRUPT")
        q_path = QUARANTINE_DIR / cap_id
        q_path.mkdir(parents=True, exist_ok=True)

        (q_path / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

        rejection_data = {
            "capability_id": cap_id,
            "rejection_timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "risk": "HIGH",
        }
        (q_path / "rejection_reason.json").write_text(json.dumps(rejection_data, indent=2, ensure_ascii=False), encoding="utf-8")
