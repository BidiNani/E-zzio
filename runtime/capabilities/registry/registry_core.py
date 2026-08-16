"""
E-ZZIO V9.2.3 — Registry Core
Base de données des compétences actives. Initialisée à vide pour garantir un contrôle strict.
"""
import json
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
REGISTRY_PATH = ROOT_DIR / "runtime" / "capabilities" / "registry" / "capability_registry.json"

class RegistryCore:
    def __init__(self):
        self.registry_file = REGISTRY_PATH
        self._init_empty_registry()

    def _init_empty_registry(self):
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_file.exists():
            initial_data = {
                "registry_version": "1.0",
                "capabilities": []
            }
            self.registry_file.write_text(json.dumps(initial_data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_state(self) -> dict:
        try:
            return json.loads(self.registry_file.read_text(encoding="utf-8"))
        except Exception:
            return {"registry_version": "1.0", "capabilities": []}
