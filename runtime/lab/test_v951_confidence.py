import sys
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from runtime.confidence.engine import ConfidenceEngine

def run_test():
    print("\n" + "="*60)
    print(" 🏛️ E-ZZIO V9.5.1 — CONFIDENCE ENGINE CERTIFICATION")
    print("="*60)

    engine = ConfidenceEngine()

    # Test 1: Haute confiance (Injecté par 50 succès préalables)
    # (Simulé par le fonctionnement interne qui lit le ledger)
    plan_normal = {"target": "web_research"}
    res_normal = engine.analyze("WF-TEST-001", plan_normal)
    print(f" Test Haute Confiance   : [{res_normal['decision']}] (Score: {res_normal['confidence']})")

    # Test 2: Invariant ECOL/Constitution (Protection ultime)
    plan_invar = {"target": "modify_constitution"}
    res_invar = engine.analyze("WF-TEST-INVAR", plan_invar)
    print(f" Test Invariant ECOL    : [{res_invar['decision']}] -> {res_invar['reason']}")

    print("-" * 60)
    print(" 🟢 STATUS : GOVERNED DECISION ENGINE ACTIVE")
    print("="*60 + "\n")

    assert res_invar['decision'] == "DENIED"

if __name__ == "__main__":
    run_test()
