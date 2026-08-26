"""
E-ZZIO V7.35 — Certification Test Suite (Evolution Simulation & Digital Twin)
Valide l'exécution en sandbox et la simulation empirique des performances.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.evolution_simulation.digital_twin import digital_twin


def run_simulation_certification():
    print("============================================================")
    print(" E-ZZIO V7.35 — DIGITAL TWIN SIMULATION CERTIFICATION")
    print("============================================================\n")

    # [1/2] Simulation d'un candidat performant et stable
    fast_candidate = "def compute():\n    x = sum(range(1000))\n    return x"
    res_fast = digital_twin.simulate_evolution(fast_candidate, baseline_max_time=0.1)
    assert res_fast["simulation_passed"] is True, f"Simulation échouée : {res_fast['reason']}"
    print(f" [1/2] Simulation candidat performant (Temps: {res_fast['execution_time']}s) : OK")

    # [2/2] Simulation d'un candidat provoquant une erreur d'exécution (définition + appel)
    crashing_candidate = "def crash():\n    raise ZeroDivisionError('Simulated crash')\ncrash()"
    res_crash = digital_twin.simulate_evolution(crashing_candidate)
    assert res_crash["simulation_passed"] is False, "Le crash en sandbox n'a pas été détecté !"
    print(" [2/2] Détection d'échec d'exécution dans le Jumeau : OK")

    print("\n============================================================")
    print(" V7.35 CERTIFIÉ : DIGITAL TWIN & SIMULATION ENGINE ACTIF")
    print("============================================================\n")


if __name__ == "__main__":
    run_simulation_certification()
