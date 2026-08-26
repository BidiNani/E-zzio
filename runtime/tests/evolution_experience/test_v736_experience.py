"""
E-ZZIO V7.36 — Certification Test Suite (Evolution Experience Ledger)
Valide l'enregistrement des propositions et la mise à jour des retours de runtime.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.evolution_experience.experience_ledger import evolution_experience_ledger


def run_experience_certification():
    print("============================================================")
    print(" E-ZZIO V7.36 — EXPERIENCE LEDGER CERTIFICATION")
    print("============================================================\n")

    evol_id = "EVOL-TEST-001"

    # [1/2] Enregistrement d'une proposition d'évolution
    rec = evolution_experience_ledger.record_proposal(
        evolution_id=evol_id,
        candidate_hash="abc123hash",
        scores={"evolution_score": 0.85},
        simulation_res={"simulation_passed": True},
        decision="PROMOTED",
    )
    assert rec["runtime_outcome"] == "PENDING", "Le statut initial doit être PENDING !"
    print(" [1/2] Enregistrement proposition d'évolution : OK")

    # [2/2] Mise à jour du résultat réel en production (Runtime Outcome)
    success = evolution_experience_ledger.update_outcome(evol_id, "SUCCESS_STABLE")
    assert success is True, "La mise à jour de l'outcome a échoué !"

    history = evolution_experience_ledger.get_history()
    target_record = next((h for h in history if h["evolution_id"] == evol_id), None)

    assert target_record is not None, "Enregistrement introuvable dans l'historique !"
    assert target_record["runtime_outcome"] == "SUCCESS_STABLE", "L'outcome n'a pas été actualisé !"
    print(f" [2/2] Actualisation du résultat runtime ({target_record['runtime_outcome']}) : OK")

    print("\n============================================================")
    print(" V7.36 CERTIFIÉ : EXPERIENCE LEDGER & FEEDBACK LOOP ACTIF")
    print("============================================================\n")


if __name__ == "__main__":
    run_experience_certification()
