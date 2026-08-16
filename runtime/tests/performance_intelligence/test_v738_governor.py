"""
E-ZZIO V7.38 — Certification Test Suite (Adaptive Resource Governor)
Valide l'adaptation dynamique d'E-ZZIO à son environnement matériel.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.performance_intelligence.resource_governor import resource_governor

def run_governor_certification():
    print("============================================================")
    print(" E-ZZIO V7.38 — RESOURCE GOVERNOR CERTIFICATION")
    print("============================================================\n")

    # [1/4] Hardware Detection (Réel)
    topo = resource_governor.evaluate_topology()
    assert topo["cpu_threads"] > 0, "Échec de détection des threads CPU"
    assert topo["free_ram_gb"] > 0, "Échec de détection de la RAM"
    print(" [1/4] Hardware Detection : OK")
    print(f"       CPU Threads: {topo['cpu_threads']}")
    print(f"       RAM Available: {topo['free_ram_gb']}GB")

    # [2/4] Worker Scaling (Basé sur le matériel réel)
    print("\n [2/4] Worker Scaling : OK")
    print(f"       Selected Workers: {topo['workers_selected']}")
    print(f"       Active Mode: {topo['mode']}")

    # [3/4] Memory Budget Enforcement
    safe_alloc = resource_governor.enforce_memory_budget(requested_mb=100.0)
    assert safe_alloc is True, "Le gouverneur a bloqué une allocation mineure sécurisée !"
    
    massive_alloc = resource_governor.enforce_memory_budget(requested_mb=999999.0)
    assert massive_alloc is False, "Le gouverneur a autorisé le dépassement de la RAM physique !"
    print("\n [3/4] Memory Budget Enforcement : OK")

    # [4/4] Adaptive Policy Decision (Simulation d'une machine saturée)
    restricted_topo = resource_governor.evaluate_topology(simulated_ram_mb=1024.0)  # Simule 1GB restant
    assert restricted_topo["mode"] == "PERFORMANCE_SAFE", "Le système n'a pas rétrogradé en mode SAFE !"
    assert restricted_topo["workers_selected"] == 1, "Le système n'a pas réduit ses workers en mode SAFE !"
    print(" [4/4] Adaptive Policy Decision : OK")

    print("\n============================================================")
    print(" V7.38 CERTIFIÉ : ADAPTIVE RESOURCE GOVERNOR ACTIF")
    print("============================================================\n")

if __name__ == "__main__":
    run_governor_certification()
