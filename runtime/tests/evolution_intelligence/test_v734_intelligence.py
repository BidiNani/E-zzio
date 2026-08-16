"""
E-ZZIO V7.34 — Certification Test Suite (Evolution Intelligence)
Valide l'analyse d'impact et le calcul du score d'évolution.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.evolution_intelligence.evolution_scorer import evolution_scorer

def run_intelligence_certification():
    print("============================================================")
    print(" E-ZZIO V7.34 — EVOLUTION INTELLIGENCE CERTIFICATION")
    print("============================================================\n")

    # [1/2] Candidat optimisé (léger, sans boucles complexes)
    efficient_code = "def fast_math(x):\n    return x * 2"
    res_eff = evolution_scorer.compute_score(efficient_code, expected_benefit=0.8)
    assert res_eff["promotion_recommended"] is True, "L'évolution optimisée a été rejetée !"
    print(f" [1/2] Évaluation code optimisé (Score: {res_eff['evolution_score']}) : OK")

    # [2/2] Candidat lourd et risqué (boucles imbriquées massives)
    heavy_code = "def heavy_loop(n):\n    total = 0\n    for i in range(n):\n        for j in range(n):\n            for k in range(n):\n                total += i * j * k\n    return total"
    res_heavy = evolution_scorer.compute_score(heavy_code, expected_benefit=0.3)
    assert res_heavy["promotion_recommended"] is False, "Le code à fort risque de régression a été accepté !"
    print(f" [2/2] Évaluation code lourd/risqué (Score: {res_heavy['evolution_score']}) : OK")

    print("\n============================================================")
    print(" V7.34 CERTIFIÉ : INTELLIGENCE & SELF-OPTIMIZATION ACTIF")
    print("============================================================\n")

if __name__ == "__main__":
    run_intelligence_certification()
