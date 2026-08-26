from runtime.skills.loader import SkillLoader
from runtime.memory.bridge import MemoryBridge


class SkillRegistry:
    def __init__(self, active_dir: str = "runtime/skills/active"):
        self.loader = SkillLoader(active_dir)
        self.skills = self.loader.discover_skills()
        self.memory_bridge = MemoryBridge()

    def list_skills(self):
        return list(self.skills.keys())

    def execute(self, skill_name: str, params: dict):
        if skill_name in self.skills:
            skill_module = self.skills[skill_name]
            if hasattr(skill_module, "run"):
                try:
                    result = skill_module.run(params)
                    self.memory_bridge.skill_execution(skill_name, params, result)
                    return result
                except Exception as e:
                    error_result = {"success": False, "error": str(e)}
                    self.memory_bridge.skill_execution(skill_name, params, error_result)
                    return error_result
            raise AttributeError(f"Le skill '{skill_name}' ne possède pas de fonction run().")
        raise KeyError(f"Skill introuvable : {skill_name}")
