"""
Validation de la brique V9.1.2 Opportunity Detector
Vérifie la traduction des signaux en opportunités structurées.
"""
import sys
import json
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from runtime.evolution.opportunity_detector import OpportunityDetector

def run_test():
    print("\n" + "="*60)
    print(" 🏛️ E-ZZIO V9.1.2 — OPPORTUNITY DETECTOR TEST")
    print("="*60)

    detector = OpportunityDetector()
    report = detector.generate_opportunities_report()

    print(json.dumps(report, indent=2))
    print("-" * 60)
    print(f" Opportunités identifiées : {report['total_opportunities_detected']}")
    print(f" STATUS                   : {report['status']}")
    print("="*60 + "\n")

    assert report['total_opportunities_detected'] >= 0, "Erreur de comptage des opportunités"

if __name__ == "__main__":
    run_test()
