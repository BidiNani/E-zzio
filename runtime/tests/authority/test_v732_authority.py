"""
E-ZZIO V7.32 — Certification Test Suite (Authority & Evolution Governance)
Valide les 6 critères de gouvernance d'évolution.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.authority.evolution_request import evolution_request_engine
from core.authority.promotion_controller import promotion_controller
from core.authority.evolution_ledger import evolution_ledger
from core.authority.authority_policy import authority_policy_engine

def run_authority_certification():
    print("============================================================")
    print(" E-ZZIO V7.32 — AUTHORITY & GOVERNANCE CERTIFICATION")
    print("============================================================\n")

    # [1/6] Création Evolution Request
    req = evolution_request_engine.create_request(
        evolution_type="SKILL_UPGRADE",
        target="memory",
        reason="optimisation rappel"
    )
    assert req["request_id"].startswith("EVOL-"), "ID de requête invalide !"
    print(" [1/6] Création Evolution Request : OK")

    # [2/6] Rejet modification domaine protégé (ex: constitution)
    req_protected = evolution_request_engine.create_request(
        evolution_type="CORE_MUTATION",
        target="constitution",
        reason="tentative modification illégale"
    )
    assert req_protected["policy_evaluation"]["allowed"] is False, "Échec du blocage domaine protégé !"
    assert req_protected["status"] == "REJECTED", "Statut de rejet incorrect !"
    print(" [2/6] Rejet modification domaine protégé : OK")

    # [3/6] Validation Policy Engine
    eval_res = authority_policy_engine.evaluate_target("skills", "UPGRADE")
    assert eval_res["requires_validation"] is True, "Politique de validation non respectée !"
    print(" [3/6] Validation Policy Engine : OK")

    # [4/6] Chaînage Evolution Ledger
    block = evolution_ledger.append_block("test_module.py", "PASSED", "deadbeef" * 8)
    assert block["block_index"] >= 0, "Index de bloc invalide !"
    print(" [4/6] Chaînage Evolution Ledger : OK")

    # [5/6] Promotion contrôlée (avec accord mentor)
    promo_res = promotion_controller.promote_candidate(
        candidate_name="memory_optimizer.py",
        content="# Optimized memory engine v2",
        approved_by_mentor=True
    )
    assert promo_res["promoted"] is True, "Échec de la promotion contrôlée !"
    print(f" [5/6] Promotion contrôlée (Snapshot pre #{promo_res['pre_snapshot']} -> post #{promo_res['post_snapshot']}) : OK")

    # [6/6] Rollback vers snapshot V7.31
    rollback_res = promotion_controller.rollback_to_last_snapshot()
    assert rollback_res["recovered"] is True, "Échec du rollback identitaire !"
    print(" [6/6] Rollback vers snapshot V7.31 : OK")

    print("\n============================================================")
    print(" V7.32 CERTIFIÉ : AUTHORITY & EVOLUTION GOVERNANCE ACTIF")
    print("============================================================\n")

if __name__ == "__main__":
    run_authority_certification()
