from pathlib import Path
import importlib.util
from runtime.skills.validator import SkillValidator

class SkillLoader:
    def __init__(self, active_dir: str):
        self.active_dir = Path(active_dir)

    def discover_skills(self) -> dict:
        loaded_skills = {}
        if not self.active_dir.exists():
            return loaded_skills

        for skill_dir in self.active_dir.iterdir():
            if skill_dir.is_dir():
                manifest_path = skill_dir / "manifest.json"
                skill_file = skill_dir / "skill.py"

                if SkillValidator.validate_manifest(manifest_path) and skill_file.exists():
                    spec = importlib.util.spec_from_file_location(skill_dir.name, skill_file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    loaded_skills[skill_dir.name] = module
        return loaded_skills
