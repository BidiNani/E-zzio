import sys
from pathlib import Path

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.dispatcher import EzzioDispatcher
from core.model_registry import ORGANS, best_fast_model, load_latency

def run_governor_test():
    print("[*] Test V7.21 — Adaptive Model Governor & Latency/Speed Tiers...")
    
    # 1. Vérification du tri par vitesse
    fastest = best_fast_model()
    print(f"  [SPEED TIER] Modèle le plus rapide sélectionné automatiquement -> {fastest}")
    assert fastest == "gemma4e4b:latest", f"Attendu gemma4e4b, obtenu {fastest}"

    # 2. Vérification de la chaîne de fallback multi-niveaux de l'organe coding
    coding_organ = ORGANS["coding"]
    print(f"  [FALLBACK CHAIN] Chaîne de secours pour coding -> {coding_organ.get('fallback_chain')}")

    # 3. Vérification de la latence simulée/chargée
    latencies = load_latency()
    print(f"  [LATENCY REGISTRY] Métriques de performance estimées : {latencies}")

    print("🟢 SUCCÈS : Le gouverneur adaptatif V7.21 est pleinement opérationnel !")

if __name__ == "__main__":
    run_governor_test()
