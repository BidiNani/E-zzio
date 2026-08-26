"""
E-ZZIO V9.3.1 — Capability Drift Detector
Surveille l'intégrité des manifestes et détecte les élévations de privilèges ou modifications de hachage.
"""

import json
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(r"G:\AI\E-zzio")
MANIFESTS_DIR = ROOT_DIR / "runtime" / "capabilities" / "registry" / "manifests"
QUARANTINE_DIR = ROOT_DIR / "runtime" / "capabilities" / "quarantine"


class CapabilityDriftDetector:
    def __init__(self):
        pass

    def inspect_drift(self, capability_id: str, current_manifest: dict) -> dict:
        path = MANIFESTS_DIR / f"{capability_id.lower()}.json"
        if not path.exists():
            return {"status": "ERROR", "reason": "Manifeste de référence introuvable."}

        original = json.loads(path.read_text(encoding="utf-8"))

        # 1. Vérification des permissions (Détection d'élévation de privilèges non autorisée)
        orig_perms = set(original.get("permissions", []))
        curr_perms = set(current_manifest.get("permissions", []))

        if not curr_perms.issubset(orig_perms):
            unauthorized = curr_perms - orig_perms
            reason = f"Permission escalation detected: {unauthorized}"
            self._quarantine_drifted_capability(capability_id, current_manifest, reason)
            return {"status": "DRIFT_DETECTED", "action": "QUARANTINE", "reason": reason}

        return {"status": "INTEGRITY_PASSED", "reason": "Aucune dérive ni élévation de privilège détectée."}

    def _quarantine_drifted_capability(self, capability_id: str, manifest: dict, reason: str):
        q_path = QUARANTINE_DIR / f"DRIFT_{capability_id}"
        q_path.mkdir(parents=True, exist_ok=True)
        (q_path / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

        report = {
            "capability_id": capability_id,
            "drift_timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "action": "QUARANTINE_AND_ROLLBACK",
        }
        (q_path / "drift_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
