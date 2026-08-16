from runtime.memory.event_store import MemoryEventStore
from runtime.audit.skill_audit import SkillAudit

class MemoryBridge:
    def __init__(self):
        self.memory = MemoryEventStore()
        self.audit = SkillAudit()

    def skill_execution(self, skill: str, args: dict, result):
        self.audit.record(skill, args, result)

        event_type = "SKILL_EXECUTED"
        if isinstance(result, dict) and (result.get("success") is False or "error" in result):
            event_type = "SKILL_FAILED"

        return self.memory.append(
            event_type,
            {
                "skill": skill,
                "arguments": args,
                "result": result
            },
            {"interface": "cli", "version": "4.3"}
        )

    def snapshot(self):
        return self.memory.recent(20)