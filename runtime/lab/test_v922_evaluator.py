"""
Validation de la brique V9.2.2 Capability Evaluator
Vérifie le blocage basé sur la règle HW-001 et l'approbation des skills conformes.
"""
import sys
import json
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from runtime.capabilities.evaluator import CapabilityEvaluator

def run_test():
    print("\n" + "="*60)
    print(" 🏛️ E-ZZIO V9.2.2 — CAPABILITY EVALUATOR TEST")
    print("="*60)

    evaluator = CapabilityEvaluator()

    # Cas 1 : Skill lourd exigeant le GPU local (Doit être rejeté par HW-001)
    bad_manifest = {
        "skill_id": "local_stable_diffusion",
        "version": "1.0",
        "permissions": ["filesystem_write"],
        "memory_cost_mb": 4000,
        "gpu_required": True,
        "rollback_available": True
    }

    # Cas 2 : Skill léger basé sur le cloud (Doit être approuvé)
    good_manifest = {
        "skill_id": "gemini_image_generator",
        "version": "1.0",
        "permissions": ["network"],
        "memory_cost_mb": 45,
        "gpu_required": False,
        "rollback_available": True
    }

    res_bad = evaluator.evaluate(bad_manifest)
    res_good = evaluator.evaluate(good_manifest)

    print(f" Test 1 (GPU Local) : [{res_bad['status']}] -> {res_bad['reason']}")
    print(f" Test 2 (Cloud API) : [{res_good['status']}] -> {res_good['reason']}")
    print("-" * 60)

    assert res_bad['status'] == "REJECTED", "Échec du filtre HW-001 !"
    assert res_good['status'] == "APPROVED", "Échec de l'approbation du skill conforme !"

    print(" 🟢 STATUS : EVALUATOR_SECURED_AND_TESTED")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_test()
