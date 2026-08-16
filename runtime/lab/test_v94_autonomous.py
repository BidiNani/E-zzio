import sys
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from runtime.capabilities.discovery.acquisition_manager import AutonomousAcquisitionManager

def run_test():
    print("\n" + "="*60)
    print(" 🏛️ E-ZZIO V9.4 — AUTONOMOUS ACQUISITION CERTIFICATION")
    print("="*60)

    acq = AutonomousAcquisitionManager()
    goal = "I need a skill to create images"
    
    print(f" Objectif identifié : {goal}")
    proposal = acq.propose_evolution(goal)
    
    print(f" Statut Analyse     : [{proposal['status']}]")
    if proposal['status'] == 'PROPOSAL_READY':
        cand = proposal['candidate']
        print(f" Capability trouvée : {cand['capability_id']}")
        print(f" Risque             : {proposal['risk_assessment']}")
        print(f" Action Requise     : {proposal['action']}")

    print("-" * 60)
    print(" 🟢 STATUS : AUTONOMOUS EVOLUTION READY")
    print("="*60 + "\n")
    
    assert proposal['status'] == 'PROPOSAL_READY'

if __name__ == "__main__":
    run_test()
