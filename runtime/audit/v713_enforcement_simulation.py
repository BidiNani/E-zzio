import sys
from pathlib import Path

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from runtime.contracts.enforcer import EnforcedModelRouter, UnauthorizedModelError

def simulate_routing():
    router = EnforcedModelRouter()
    
    print("\n--- Scénario 1 : Appel d'un modèle gouverné (qwen2.5-coder:7b) ---")
    try:
        res = router.route_inference("qwen2.5-coder:7b")
        print(f"  Résultat : {res['status']}")
    except Exception as e:
        print(f"  ❌ Échec inattendu : {str(e)}")

    print("\n--- Scénario 2 : Tentative de Shadow Inference (fake-shadow-model:999) ---")
    try:
        res = router.route_inference("fake-shadow-model:999")
        print(f"  ❌ ERREUR GRAVE : Le routage a réussi alors qu'il aurait dû être bloqué !")
    except UnauthorizedModelError as ume:
        print(f"  🟢 SUCCÈS DU BLOCAGE : {str(ume)}")

if __name__ == "__main__":
    simulate_routing()
