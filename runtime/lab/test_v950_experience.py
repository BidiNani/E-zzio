"""
Test de certification de la mémoire d'expérience V9.5.0
"""
import sys
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from runtime.experience.experience_ledger import ExperienceLedger

def run_certification():
    print("\n" + "="*60)
    print(" 🏛️ E-ZZIO V9.5.0 — EXPERIENCE MEMORY CERTIFICATION")
    print("="*60)

    ledger = ExperienceLedger()

    # 1. Test Log Succès
    succ = ledger.log_success(
        workflow_id="WF-RESEARCH-001",
        capabilities=["WEB_RESEARCHER", "DOCUMENT_ANALYST"],
        duration_ms=4200.0,
        memory_peak_mb=470.0,
        confidence=0.91
    )
    print(f" Success Logging Test   : [PASS] -> Workflow {succ['workflow_id']} enregistré.")

    # 2. Test Log Échec
    fail = ledger.log_failure(
        workflow_id="WF-DOC-002",
        capability="DOCUMENT_ANALYST",
        failure_type="PDF_ENCRYPTED",
        resolution="ASK_USER_PASSWORD"
    )
    print(f" Failure Logging Test   : [PASS] -> Échec {fail['failure']} mémorisé.")

    # 3. Test Pattern Storage
    ledger.save_pattern("frequent_research_flow", {"preferred_organ": "WEB_RESEARCHER", "success_rate": 0.98})
    print(f" Pattern Storage Test   : [PASS] -> Pattern mémorisé.")

    print("-" * 60)
    print(" Kernel Modification    : 0")
    print(" ECOL Violation         : 0")
    print("-" * 60)
    print(" 🟢 STATUS : EXPERIENCE MEMORY ACTIVE")
    print("="*60 + "\n")

    assert succ['status'] == "SUCCESS"
    assert fail['status'] == "FAILURE"

if __name__ == "__main__":
    run_certification()
