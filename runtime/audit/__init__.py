from .logger import AuditLogger
from .skill_audit import SkillAudit

class AuditAction:
    PASS = "PASS"
    DENY = "DENY"

class AuditBridge:
    def log(self, action, details):
        pass

__all__ = ["AuditLogger", "SkillAudit", "AuditAction", "AuditBridge"]
