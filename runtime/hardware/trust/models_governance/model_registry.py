import json
from pathlib import Path


class ModelTrustRegistry:
    def __init__(self, registry_file: Path):
        self.registry_file = registry_file
        self._load_registry()

    def _load_registry(self):
        if not self.registry_file.exists():
            # Registre par défaut intégrant les modèles connus
            default_data = {
                "qwen2.5-7b": {"status": "TRUSTED", "max_allowed_workers": 8, "max_ram_mb": 8192},
                "qwen2.5-3b": {"status": "TRUSTED", "max_allowed_workers": 4, "max_ram_mb": 4096},
                "gemini-pro": {"status": "TRUSTED_REMOTE", "max_allowed_workers": 2, "max_ram_mb": 1024},
                "unknown-model": {"status": "QUARANTINE", "max_allowed_workers": 0, "max_ram_mb": 0},
            }
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
            self.registry_file.write_text(json.dumps(default_data, indent=4), encoding="utf-8")
            self.data = default_data
        else:
            try:
                self.data = json.loads(self.registry_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self.data = {}

    def get_model_status(self, model_id: str) -> dict:
        """Retourne le statut de confiance et les budgets alloués au modèle."""
        if model_id not in self.data:
            return {"status": "QUARANTINE", "max_allowed_workers": 0, "max_ram_mb": 0}
        return self.data[model_id]
