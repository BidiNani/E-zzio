"""
E-ZZIO V7.61.8 — Réinitialisation et scellement du premier bloc canonique (Genesis).
"""

import sys
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.cognition.cognitive_governor import CognitiveGovernor

LEDGER_PATH = ROOT_DIR / "runtime" / "cognition" / "budget" / "cognitive_budget_ledger.jsonl"


def reset_ledger():
    print("[*] Réinitialisation du Token Ledger au format canonique V7.61.7...")
    if LEDGER_PATH.exists():
        backup = LEDGER_PATH.with_suffix(".jsonl.pre-industrial.bak")
        LEDGER_PATH.rename(backup)
        print(f"  + Ancien ledger sauvegardé vers : {backup.name}")

    # Instanciation d'un nouveau Governor (création propre du premier enregistrement canonique)
    gov = CognitiveGovernor()
    res = gov.evaluate_and_record("ECOL_INDUSTRIAL_GENESIS", 100, "critical", "low")
    print(f"  + Bloc Genesis canonique scellé avec succès : {res['record_hash']}")


if __name__ == "__main__":
    reset_ledger()
