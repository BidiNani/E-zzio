import os
from pathlib import Path

ROOT = Path(r"G:\AI\E-zzio")

# 1. Suppression du fichier conflictuel
shadow_file = ROOT / "runtime" / "audit.py"
if shadow_file.exists():
    shadow_file.unlink()
    print("[OK] Fichier conflictuel runtime/audit.py supprimé.")

# 2. Configuration propre du package runtime/audit/__init__.py
audit_init = ROOT / "runtime" / "audit" / "__init__.py"
audit_init.parent.mkdir(parents=True, exist_ok=True)

audit_init_content = """from .logger import AuditLogger
from .skill_audit import SkillAudit

class AuditAction:
    PASS = "PASS"
    DENY = "DENY"

class AuditBridge:
    def log(self, action, details):
        pass

__all__ = ["AuditLogger", "SkillAudit", "AuditAction", "AuditBridge"]
"""

audit_init.write_text(audit_init_content, encoding="utf-8")
print("[OK] Package runtime/audit/__init__.py configuré.")
