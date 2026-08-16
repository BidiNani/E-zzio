class EzzioSkillManager:
    def __init__(self):
        self.skills = {}

    def register_skill(self, name: str, handler):
        self.skills[name] = handler
