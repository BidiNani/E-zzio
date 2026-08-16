"""
E-ZZIO V7.39 & V7.41 — Certification Test Suite
Valide la barrière anti-régression et le moteur de recherche cognitif.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.evolution_intelligence.regression_detector import regression_detector
from core.agent.research_engine import research_engine

def run_parallel_certification():
    print("============================================================")
    print(" E-ZZIO V7.39 & V7.41 — DUAL LAYER CERTIFICATION")
    print("============================================================\n")

    # --- TEST V7.39 : REGRESSION DETECTOR ---
    print(" [V7.39] REGRESSION INTELLIGENCE")
    baseline = {"execution_time": 1.0, "memory_mb": 100.0}
    
    # Évolution optimisée (Plus rapide, moins de RAM)
    cand_better = {"execution_time": 0.88, "memory_mb": 92.0}
    res_better = regression_detector.evaluate_regression(baseline, cand_better)
    assert res_better["regression_detected"] is False, "Faux positif sur une amélioration !"
    print(f"  -> Analyse Optimisation : OK (Temps {res_better['performance_delta']}, RAM {res_better['memory_delta']})")

    # Évolution dégradée (Plus lente, tolérance dépassée)
    cand_worse = {"execution_time": 1.25, "memory_mb": 102.0}
    res_worse = regression_detector.evaluate_regression(baseline, cand_worse, time_tolerance=0.05)
    assert res_worse["regression_detected"] is True, "Régression non détectée !"
    assert res_worse["promotion_allowed"] is False, "Promotion illégalement autorisée !"
    print(f"  -> Analyse Régression : OK (Dégradation de {res_worse['performance_delta']} interceptée)")
    print("  => V7.39 CERTIFIÉ\n")

    # --- TEST V7.41 : RESEARCH ENGINE ---
    print(" [V7.41] KNOWLEDGE & RESEARCH ENGINE")
    query = "API Discord Rate Limits"
    research_res = research_engine.execute_research(query)
    
    assert research_res["confidence"] > 0.8, "Score de confiance trop bas."
    assert research_res["stored"] is True, "La synthèse n'a pas été stockée en mémoire."
    assert research_res["sources_checked"] > 0, "Aucune source simulée consultée."
    
    print(f"  -> Requête analysée : '{research_res['query']}'")
    print(f"  -> Sources vérifiées : {research_res['sources_checked']}")
    print(f"  -> Confiance cognitive : {research_res['confidence'] * 100}%")
    print(f"  -> Stockage mémoire : {'Actif' if research_res['stored'] else 'Échec'}")
    print("  => V7.41 CERTIFIÉ")

    print("\n============================================================")
    print(" STATUS : AUTONOMOUS AGENT LAYER (STAGE 1) INITIALIZED")
    print("============================================================\n")

if __name__ == "__main__":
    run_parallel_certification()
