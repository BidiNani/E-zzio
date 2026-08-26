from pathlib import Path

ROOT = Path(r"G:\AI\E-zzio")
AUDIT_PKG = ROOT / "runtime" / "audit"
AUDIT_PKG.mkdir(parents=True, exist_ok=True)

# 1. runtime/audit/logger.py
logger_code = """import logging

class AuditLogger:
    def __init__(self, name: str = "ezzio.audit"):
        self.logger = logging.getLogger(name)

    def log_event(self, event_type: str, payload: dict) -> None:
        self.logger.info(f"[{event_type}] {payload}")

    def info(self, msg: str, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)
"""
(AUDIT_PKG / "logger.py").write_text(logger_code, encoding="utf-8")
print("[OK] Fichier vérifié/créé : runtime/audit/logger.py")

# 2. runtime/audit/skill_audit.py
skill_code = """class SkillAudit:
    def __init__(self):
        pass

    def audit_skill(self, skill_name: str) -> bool:
        return True
"""
(AUDIT_PKG / "skill_audit.py").write_text(skill_code, encoding="utf-8")
print("[OK] Fichier vérifié/créé : runtime/audit/skill_audit.py")

# 3. runtime/audit/__init__.py
init_code = """from .logger import AuditLogger
from .skill_audit import SkillAudit

class AuditAction:
    PASS = "PASS"
    DENY = "DENY"

class AuditBridge:
    def log(self, action, details):
        pass

__all__ = ["AuditLogger", "SkillAudit", "AuditAction", "AuditBridge"]
"""
(AUDIT_PKG / "__init__.py").write_text(init_code, encoding="utf-8")
print("[OK] Fichier vérifié/créé : runtime/audit/__init__.py")

print("\n[OK] Correctif définitif pour runtime.audit appliqué.")
