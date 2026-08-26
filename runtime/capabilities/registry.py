"""
E-ZZIO V9.2.1 — Capability Registry
Gère l'inventaire local des compétences de l'organisme et applique la Capability Constitution.
"""

import json
from pathlib import Path
from typing import Dict, Any

ROOT_DIR = Path(r"G:\AI\E-zzio")
REGISTRY_PATH = ROOT_DIR / "runtime" / "capabilities" / "capability_registry.json"


class CapabilityRegistry:
    def __init__(self):
        self.registry_file = REGISTRY_PATH
        self._ensure_registry()

    def _ensure_registry(self):
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_file.exists():
            initial_data = {
                "registered_capabilities": [
                    {
                        "skill_id": "proprioception_sense",
                        "version": "1.0",
                        "permissions": ["system_read"],
                        "memory_cost_mb": 15,
                        "gpu_required": False,
                        "rollback_available": True,
                        "ecol_compliance": "VERIFIED",
                    },
                    {
                        "skill_id": "evolution_observer",
                        "version": "1.0",
                        "permissions": ["ledger_read"],
                        "memory_cost_mb": 25,
                        "gpu_required": False,
                        "rollback_available": True,
                        "ecol_compliance": "VERIFIED",
                    },
                ]
            }
            self.registry_file.write_text(json.dumps(initial_data, indent=2, ensure_ascii=False), encoding="utf-8")

    def load_registry(self) -> Dict[str, Any]:
        try:
            return json.loads(self.registry_file.read_text(encoding="utf-8"))
        except Exception:
            return {"registered_capabilities": []}

    def is_capability_active(self, skill_id: str) -> bool:
        data = self.load_registry()
        for cap in data.get("registered_capabilities", []):
            if cap.get("skill_id") == skill_id:
                return True
        return False

    def register_capability(self, capability_manifest: dict) -> bool:
        required_fields = ["skill_id", "version", "permissions", "memory_cost_mb", "gpu_required", "rollback_available"]
        for field in required_fields:
            if field not in capability_manifest:
                return False

        data = self.load_registry()
        for cap in data["registered_capabilities"]:
            if cap["skill_id"] == capability_manifest["skill_id"]:
                return False  # Déjà enregistré

        capability_manifest["ecol_compliance"] = "VERIFIED"
        data["registered_capabilities"].append(capability_manifest)
        self.registry_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return True


if __name__ == "__main__":
    registry = CapabilityRegistry()
    print(json.dumps(registry.load_registry(), indent=2))
