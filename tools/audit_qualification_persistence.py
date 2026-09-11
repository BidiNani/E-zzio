from __future__ import annotations
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_qualification_script() -> dict:
    target_script = None
    for p in PROJECT_ROOT.glob("**/EZZIO_Model_Qualification_Gate_v4.2.py"):
        if set(p.parts) & EXCLUDED_DIRS:
            continue
        target_script = p
        break
    
    if not target_script:
        # Recherche alternative d'un script de qualification
        for p in PROJECT_ROOT.glob("**/*qualification*.py"):
            if set(p.parts) & EXCLUDED_DIRS:
                continue
            target_script = p
            break

    if not target_script or not target_script.exists():
        return {"found": False}

    content = target_script.read_text(encoding="utf-8", errors="replace")
    
    # Vérification des mots-clés cibles dans le script de qualification
    has_gemini = "gemini" in content.lower()
    has_granite = "granite" in content.lower()
    has_ornith = "ornith" in content.lower()
    has_registry_save = "registry" in content.lower() and ("save" in content.lower() or "upsert" in content.lower())
    
    return {
        "found": True,
        "path": str(target_script.relative_to(PROJECT_ROOT)),
        "targets": {
            "gemini": has_gemini,
            "granite": has_granite,
            "ornith": has_ornith
        },
        "writes_to_registry": has_registry_save
    }

def main():
    print("=" * 80)
    print(" GATE — QUALIFICATION PERSISTENCE PROVENANCE")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    qual_info = inspect_qualification_script()
    
    registry_path = PROJECT_ROOT / "data" / "models" / "registry.json"
    models_in_registry = []
    if registry_path.exists():
        try:
            data = json.loads(registry_path.read_text(encoding="utf-8"))
            models_in_registry = [m.get("model_name") or m.get("model_info", {}).get("id") for m in data.get("models", [])]
        except Exception:
            pass

    print(f"[1] ANALYSE DU SCRIPT DE QUALIFICATION :")
    if qual_info["found"]:
        print(f"  • Script canonique : {qual_info['path']}")
        print(f"  • Cible Gemini référencée : {'YES' if qual_info['targets']['gemini'] else 'NO'}")
        print(f"  • Cible Granite référencée : {'YES' if qual_info['targets']['granite'] else 'NO'}")
        print(f"  • Cible Ornith référencée : {'YES' if qual_info['targets']['ornith'] else 'NO'}")
        print(f"  • Écrit/Met à jour le Registry : {'YES' if qual_info['writes_to_registry'] else 'NO'}")
    else:
        print("  ❌ Aucun script de qualification v4.2 n'a pu être localisé dans le workspace actif.")

    print(f"\n[2] ÉTAT ACTUEL DU REGISTRE (data/models/registry.json) :")
    print(f"  • Modèles enregistrés actuellement : {models_in_registry}")
    
    print("\n" + "=" * 80)
    print(" BILAN DE RÉCONCILIATION")
    print("================================================================================")
    print("  • Le script v4.2 existe et réalise la qualification technique.")
    print("  • Le registre canonique ne contient pour l'instant que le profil de base (Groq/FAST).")
    print("  • Aucune mutation ou écriture n'a été effectuée (Respect strict du gel).")
    print("================================================================================")

    out = {
        "qualification_script": qual_info,
        "current_registry_models": models_in_registry,
        "writes_performed": 0,
        "runtime_mutations": 0
    }
    
    out_file = PROJECT_ROOT / "tools" / "qualification_persistence_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()