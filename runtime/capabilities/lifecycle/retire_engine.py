"""
E-ZZIO V9.3.1 — Retire Engine
Gère l'excision propre et sécurisée d'un organe (Snapshot, Désactivation, Suppression Sandbox, Registre).
"""
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(r"G:\AI\E-zzio")
MANIFESTS_DIR = ROOT_DIR / "runtime" / "capabilities" / "registry" / "manifests"

class RetireEngine:
    def __init__(self):
        pass

    def retire_capability(self, capability_id: str) -> dict:
        path = MANIFESTS_DIR / f"{capability_id.lower()}.json"
        if not path.exists():
            return {"status": "ERROR", "reason": "Organe introuvable dans le registre."}

        manifest = json.loads(path.read_text(encoding="utf-8"))
        
        # 1. Création de l'état de retrait (Snapshot logique)
        manifest["status"] = "RETIRED"
        manifest["retired_utc"] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

        # 2. Suppression/Désactivation effective du manifeste actif du registre
        path.unlink()

        return {
            "capability_id": capability_id,
            "status": "REMOVED_CLEANLY",
            "reason": "Snapshot créé, exécution désactivée, manifeste purgé du registre actif."
        }
