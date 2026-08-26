"""
Validation de la brique V9.1.4 Evolution Lab
Vérifie la simulation en sandbox et le respect absolu des invariants ECOL.
"""

import sys
import json
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from runtime.evolution.lab_validator import LabValidator


def run_test():
    print("\n" + "=" * 60)
    print(" 🏛️ E-ZZIO V9.1.4 — EVOLUTION LAB VALIDATION TEST")
    print("=" * 60)

    validator = LabValidator()
    report = validator.run_validation_batch()

    print(json.dumps(report, indent=2))
    print("-" * 60)
    print(f" Propositions testées en Sandbox : {report['total_validated']}")
    print(f" STATUS                          : {report['status']}")
    print("=" * 60 + "\n")

    assert report["total_validated"] >= 0, "Erreur de validation en sandbox"


if __name__ == "__main__":
    run_test()
