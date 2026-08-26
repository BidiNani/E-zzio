"""
E-ZZIO V7.37 — Certification Test Suite (Performance Intelligence)
Valide le profilage d'exécution, la mesure mémoire et le calcul d'optimisation.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.performance_intelligence.runtime_profiler import runtime_profiler
from core.performance_intelligence.optimization_scorer import optimization_scorer


# Fonctions de test simulant des charges de travail
def lightweight_workload():
    return sum(range(10000))


def heavy_memory_workload():
    # Crée une large liste en mémoire pour simuler une surcharge RAM
    large_list = [x for x in range(1000000)]
    return len(large_list)


def run_performance_certification():
    print("============================================================")
    print(" E-ZZIO V7.37 — PERFORMANCE INTELLIGENCE CERTIFICATION")
    print("============================================================\n")

    # [1/3] Profiling runtime (Charge légère)
    prof_light = runtime_profiler.profile_execution(lightweight_workload)
    assert prof_light["error"] is None, "Erreur d'exécution de la charge légère"
    assert "execution_time" in prof_light["metrics"], "Temps non profilé"
    print(
        f" [1/3] Profiling runtime (Temps: {prof_light['metrics']['execution_time']}s, RAM: {prof_light['metrics']['memory_mb']} MB) : OK"
    )

    # [2/3] Détection surcharge mémoire (Charge lourde)
    prof_heavy = runtime_profiler.profile_execution(heavy_memory_workload)
    assert prof_heavy["metrics"]["memory_mb"] > prof_light["metrics"]["memory_mb"], "Le pic mémoire n'a pas été détecté !"
    print(f" [2/3] Détection surcharge mémoire (RAM Pic: {prof_heavy['metrics']['memory_mb']} MB) : OK")

    # [3/3] Calcul optimisation
    # Évaluation de la charge lourde avec des cibles très strictes (ex: max 0.01s et 1MB)
    score_res = optimization_scorer.calculate_score("heavy_workload", prof_heavy["metrics"], target_time=0.01, target_ram_mb=1.0)
    assert "optimization_score" in score_res, "Score non calculé"

    # Évaluation de la charge légère avec des cibles normales
    score_light = optimization_scorer.calculate_score("light_workload", prof_light["metrics"], target_time=0.1, target_ram_mb=5.0)

    print(
        f" [3/3] Calcul optimisation (Score Léger: {score_light['optimization_score']}, Score Lourd: {score_res['optimization_score']}) : OK"
    )

    print("\n============================================================")
    print(" V7.37 CERTIFIÉ : RUNTIME PERFORMANCE INTELLIGENCE ACTIF")
    print("============================================================\n")


if __name__ == "__main__":
    run_performance_certification()
