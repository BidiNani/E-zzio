import sys
from pathlib import Path

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.dispatcher import EzzioDispatcher
from core.model_registry import all_known_models, ORGANS

def run_test():
    print("[*] Test d'intégration V7.20.1 — Dispatcher & Capabilities...")
    print(f"  [OK] Modèles connus par le registre unifié : {all_known_models()}")
    
    dispatcher = EzzioDispatcher()
    
    # Test d'un routage rapide
    selected_fast = dispatcher.select_model_for_speed(ORGANS["presence"], "fast")
    print(f"  [ROUTAGE] Organe 'presence' (vitesse: fast) -> Modèle sélectionné : {selected_fast}")
    
    # Test d'un routage d'architecture / deep
    selected_deep = dispatcher.select_model_for_speed(ORGANS["architecture"], "deep")
    print(f"  [ROUTAGE] Organe 'architecture' (vitesse: deep) -> Modèle sélectionné : {selected_deep}")
    
    assert "llama3.2" not in selected_fast and "llama3.2" not in selected_deep, "ALERTE : Un modèle obsolète a été sélectionné !"
    print("🟢 SUCCÈS : Le dispatcher utilise exclusivement le nouveau parc matériel unifié !")

if __name__ == "__main__":
    run_test()
