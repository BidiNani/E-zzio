from __future__ import annotations
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

def main():
    print("=" * 80)
    print(" GATE v6.45.48 — CANONICAL RUNTIME RESOLUTION BRIDGE FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    try:
        from core.models.fabric import build_fabric
        from core.intents.fabric_connector import IntentFabricConnector
        
        print("[1] INSTANCIATION DE AutonomousModelFabric (build_fabric) :")
        fabric = build_fabric(project_root=PROJECT_ROOT)
        print(f"  • Instance de Fabric créée avec succès.")
        
        # Q1 & Q2 : Chemin du registre chargé
        reg = getattr(fabric, "registry", None)
        reg_path = getattr(reg, "path", getattr(reg, "_path", "Inconnu"))
        print(f"\n[2] PROVENANCE DU REGISTRE :")
        print(f"  • Chemin effectif du fichier de registre : {reg_path}")
        
        # Q3 : Contenu réel au démarrage
        all_recs = reg.all() if reg and hasattr(reg, "all") else []
        active_recs = reg.active() if reg and hasattr(reg, "active") else []
        print(f"  • Total enregistrements chargés : {len(all_recs)}")
        print(f"  • Enregistrements ACTIVE : {len(active_recs)}")
        for rec in active_recs:
            print(f"    ↳ ACTIVE: {getattr(rec, 'provider', '?')}/{getattr(rec, 'model_id', '?')} [Tier: {getattr(rec, 'tier', '?')}]")

        # Q4 : Routeur attaché
        router = getattr(fabric, "router", None)
        router_type = type(router).__name__ if router else "Aucun"
        model_list = getattr(router, "model_list", []) if router else []
        print(f"\n[3] ROUTEUR DE LA FABRIC :")
        print(f"  • Type de router : {router_type}")
        print(f"  • Modèles configurés dans le routeur : {len(model_list)}")
        for m in model_list:
            print(f"    ↳ {m}")

        # Q5 : Test du pont de résolution Intent / Tier -> Modèle
        print(f"\n[4] TEST DU PONT DE RÉSOLUTION INTENT/TIER :")
        connector = IntentFabricConnector(fabric=fabric, project_root=str(PROJECT_ROOT))
        for test_intent in ["quick", "code_simple", "deep_reasoning"]:
            tier = connector.resolve_tier(test_intent)
            print(f"  • Intent '{test_intent}' → Palier résolu : '{tier}'")
            
        out_report = {
            "registry_path": str(reg_path),
            "total_records": len(all_recs),
            "active_records": len(active_recs),
            "router_type": router_type,
            "router_models": model_list
        }
        out_file = PROJECT_ROOT / "tools" / "gate_v6_45_48_report.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(out_report, f, indent=2)
        print(f"\n[+] Rapport d'arbitrage exporté : {out_file}")

    except Exception as e:
        print(f"\n❌ ERREUR LORS DE L'EXÉCUTION DU GATE : {e}")
        import traceback
        traceback.print_exc()

    print("=" * 80)

if __name__ == "__main__":
    main()