"""
E-ZZIO V9.3 — Capability Lifecycle Manager
Gère la progression biologique des organes à travers les états de validation.
"""
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(r"G:\AI\E-zzio")
MANIFESTS_DIR = ROOT_DIR / "runtime" / "capabilities" / "registry" / "manifests"

VALID_STATES = [
    "DISCOVERED",
    "QUARANTINE",
    "SECURITY_SCAN",
    "SANDBOX_TEST",
    "APPROVED",
    "ACTIVE",
    "MONITORED",
    "RETIRED"
]

class LifecycleManager:
    def __init__(self):
        MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)

    def load_manifest(self, capability_id: str) -> dict:
        path = MANIFESTS_DIR / f"{capability_id.lower()}.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def save_manifest(self, manifest: dict):
        cap_id = manifest.get("capability_id", "unknown").lower()
        path = MANIFESTS_DIR / f"{cap_id}.json"
        path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    def transition_state(self, capability_id: str, target_state: str) -> dict:
        if target_state not in VALID_STATES:
            return {"status": "ERROR", "reason": f"État cible invalide : {target_state}"}

        manifest = self.load_manifest(capability_id)
        if not manifest:
            return {"status": "ERROR", "reason": f"Manifeste introuvable pour {capability_id}"}

        current_state = manifest.get("status", "DISCOVERED")
        
        # Application de la transition biologique
        manifest["status"] = target_state
        manifest["last_transition_utc"] = datetime.now(timezone.utc).isoformat()
        self.save_manifest(manifest)

        return {
            "capability_id": capability_id,
            "previous_state": current_state,
            "current_state": target_state,
            "status": "TRANSITION_SUCCESS"
        }
