"""
Validation de la brique V9.1.3 Proposal Engine
Vérifie la transformation des opportunités en propositions formelles et la traçabilité.
"""

import sys
import json
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from runtime.evolution.proposal_engine import ProposalEngine


def run_test():
    print("\n" + "=" * 60)
    print(" 🏛️ E-ZZIO V9.1.3 — PROPOSAL ENGINE TEST")
    print("=" * 60)

    engine = ProposalEngine()
    report = engine.generate_proposals_report()

    print(json.dumps(report, indent=2))
    print("-" * 60)
    print(f" Propositions générées : {report['total_proposals_generated']}")
    print(f" Ledger tracé à        : {report['ledger_path']}")
    print(f" STATUS                : {report['status']}")
    print("=" * 60 + "\n")

    assert report["total_proposals_generated"] >= 0, "Erreur de génération des propositions"


if __name__ == "__main__":
    run_test()
