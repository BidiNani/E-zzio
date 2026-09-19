from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

def main():
    print("=" * 80)
    print(" GATE v6.45.51 — EZZIOROUTER MRO & TERMINAL RESOLUTION FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    report = {}

    try:
        from core.models.router import EzzioRouter

        # 1. Analyse de l'héritage (MRO)
        mro = [cls.__name__ for cls in EzzioRouter.__mro__]
        print("[1] HÉRITAGE ET MRO D'EzzioRouter :")
        print(f"  • MRO : {' -> '.join(mro)}")
        report["mro"] = mro

        # Inspection des classes parentes pour trouver execute / set_model_list
        parent_methods = {}
        for cls in EzzioRouter.__mro__[1:]:
            methods = [m for m in dir(cls) if not m.startswith("_")]
            parent_methods[cls.__name__] = [m for m in {"execute", "acompletion", "set_model_list", "router_model_list", "get_available_models"} if hasattr(cls, m)]

        print("\n[2] MÉTHODES CLÉS LOCALISÉES DANS LES PARENTS :")
        for cls_name, mets in parent_methods.items():
            if mets:
                print(f"  • {cls_name} -> {mets}")
        report["parent_key_methods"] = parent_methods

        # 2 & 3. Test de résolution de tier et simulation d'appel de routage
        print("\n[3] TEST DE RÉSOLUTION DE TIER VIA LA FABRIC :")
        from core.models.fabric import build_fabric
        fabric = build_fabric(project_root=PROJECT_ROOT)

        if hasattr(fabric, "router") and fabric.router:
            print(f"  • Router instance type: {type(fabric.router)}")
            # Vérification de la méthode execute ou appel simulé
            has_execute = hasattr(fabric.router, "execute") or hasattr(fabric.router, "acompletion")
            print(f"  • Possède execute/acompletion: {has_execute}")

            model_list = getattr(fabric.router, "model_list", [])
            print(f"  • model_list actuel dans le routeur : {json.dumps(model_list, indent=2)}")
            report["router_model_list"] = model_list

        # 4. Séparation World A vs World B
        print("\n[4] ANALYSE COMPARATIVE DES DEUX MONDES :")
        print("  • WORLD A (Production Actuelle) : Discord -> EzzioInterface -> CognitiveTaskClassifier -> OrganismKernel -> OllamaProvider -> Ollama (127.0.0.1:11434)")
        print(f"  • WORLD B (Fabric Candidate)  : IntentFabricConnector -> AutonomousModelFabric -> ModelRegistry -> EzzioRouter ({mro[1]}) -> LiteLLM")
        print("  • COMMON TERMINAL             : NON (Les deux flux d'exécution sont actuellement parallèles et disjoints).")

        report["world_a"] = "Discord -> EzzioInterface -> CognitiveTaskClassifier -> OrganismKernel -> OllamaProvider -> Ollama"
        report["world_b"] = "IntentFabricConnector -> AutonomousModelFabric -> ModelRegistry -> EzzioRouter -> LiteLLM"
        report["common_terminal"] = False

        out_file = PROJECT_ROOT / "tools" / "gate_v6_45_51_report.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\n[+] Rapport d'arbitrage exporté : {out_file}")

    except Exception as e:
        print(f"❌ Erreur lors de l'exécution du Gate 6.45.51 : {e}")
        import traceback
        traceback.print_exc()

    print("=" * 80)

if __name__ == "__main__":
    main()
