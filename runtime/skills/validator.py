import json
from pathlib import Path


class SkillValidator:
    @staticmethod
    def validate_manifest(manifest_path: Path) -> bool:
        if not manifest_path.exists():
            return False
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            required = ["name", "version", "capabilities", "permissions"]
            return all(k in data for k in required)
        except Exception:
            return False
