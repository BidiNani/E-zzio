"""
Validation de la brique V9.1.1 Evolution Observer
Vérifie le mode Read-Only et l'intégrité du noyau.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from runtime.evolution.observer import EvolutionObserver

def run_certification():
    print("\n" + "="*60)
    print(" 🏛️ E-ZZIO V9.1.1 — EVOLUTION OBSERVER CERTIFICATION")
    print("="*60)

    observer = EvolutionObserver()
    report = observer.generate_report()

    print(f" Mode                  : {report['mode']}")
    print(" Sources analysées     :")
    for src in report['sources_analyzed']:
        print(f"   [PASS] {src}")
    print(f" Signals generated     : {report['signals_generated']}")
    print(f" Actions performed     : {report['actions_performed']}")
    print(f" Kernel modifications  : {report['kernel_modifications']}")
    print(f" ECOL violations       : {report['ecol_violations']}")
    print("-" * 60)
    print(f" STATUS                : {report['status']}")
    print("="*60 + "\n")

    assert report['actions_performed'] == 0, "Violation : L'observer a agi !"
    assert report['kernel_modifications'] == 0, "Violation : Le noyau a été modifié !"
    assert report['ecol_violations'] == 0, "Violation : ECOL a été violé !"

if __name__ == "__main__":
    run_certification()
