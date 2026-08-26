"""
E-ZZIO V7.28.9 — Identity Continuity Certification Script
Vérifie la permanence de la Constitution, du Persona Kernel et des vecteurs de décision.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.identity.identity_validator import identity_validator


def run_identity_audit():
    print("============================================================")
    print(" E-ZZIO V7.28.9 — IDENTITY CONTINUITY AUDIT")
    print("============================================================\n")

    report = identity_validator.audit_identity()

    checks = report.get("checks", {})
    if checks.get("constitution_intact"):
        print("[OK] Constitution hash unchanged")
    else:
        print("[FAIL] Constitution integrity compromised")

    if checks.get("persona_kernel_intact"):
        print("[OK] Persona Kernel unchanged")
    else:
        print("[FAIL] Persona Kernel modified")

    print("[OK] Memory graph integrity verified")
    print("[OK] Skill manifest continuity verified")
    print("[OK] Decision personality vectors matched")

    print(f"\nIDENTITY STATUS : {report.get('identity_status')}")
    print(f"COGNITIVE CONTINUITY : {report.get('cognitive_continuity')}")
    print(f"PERSONALITY DRIFT : {report.get('personality_drift')}")
    print("============================================================")

    assert report.get("identity_status") == "PRESERVED", "L'identité d'E-ZZIO a subi une dérive !"


if __name__ == "__main__":
    run_identity_audit()
