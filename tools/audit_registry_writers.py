from __future__ import annotations
import json
import ast
import sys
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_registry_writers() -> List[Dict[str, Any]]:
    results = []
    patterns = {"ModelRecord", "upsert", "save", "ModelRegistry", "ingest", "activate"}
    
    for p in PROJECT_ROOT.glob("**/*.py"):
        if set(p.parts) & EXCLUDED_DIRS:
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            content_lower = content.lower()
            
            # Vérifier si le fichier manipule le registre ou des enregistrements
            has_record = "modelrecord" in content_lower
            has_upsert = "upsert" in content_lower
            has_save = "save(" in content_lower or "save_registry" in content_lower
            
            if has_record or has_upsert or has_save:
                rel_path = str(p.relative_to(PROJECT_ROOT))
                results.append({
                    "file": rel_path,
                    "has_model_record": has_record,
                    "has_upsert": has_upsert,
                    "has_save": has_save,
                    "mentions_gemini": "gemini" in content_lower,
                    "mentions_granite": "granite" in content_lower,
                    "mentions_ornith": "ornith" in content_lower
                })
        except Exception:
            continue
    return results

def main():
    print("=" * 80)
    print(" GATE — REGISTRY WRITER AUTHORITY FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    writers = inspect_registry_writers()

    print("[WRITERS] Fichiers manipulant l'écriture/les records du Registre :\n")
    canonical_writer = "ABSENT / NON DÉTERMINÉ"
    
    for w in writers:
        print(f"  • Fichier : {w['file']}")
        print(f"    - ModelRecord(...) : {'YES' if w['has_model_record'] else 'NO'}")
        print(f"    - registry.upsert(...) : {'YES' if w['has_upsert'] else 'NO'}")
        print(f"    - registry.save() : {'YES' if w['has_save'] else 'NO'}")
        print(f"    - Référence Gemini / Granite / Ornith : {w['mentions_gemini']} / {w['mentions_granite']} / {w['mentions_ornith']}")
        print("")
        if w['has_upsert'] and w['has_save'] and not canonical_writer.startswith("EXISTS"):
            canonical_writer = w['file']

    print("--------------------------------------------------------------------------------")
    print(" [CAPABILITY INPUT]")
    print(f" Gemini  : {'DISCOVERED' if any(w['mentions_gemini'] for w in writers) else 'ABSENT'}")
    print(f" Granite : {'DISCOVERED' if any(w['mentions_granite'] for w in writers) else 'ABSENT'}")
    print(f" Ornith  : {'DISCOVERED' if any(w['mentions_ornith'] for w in writers) else 'ABSENT'}")

    print("\n [AUTHORITY]")
    print(f" Canonical Registry Writer : {canonical_writer}")

    print("\n [VERDICT]")
    if canonical_writer != "ABSENT / NON DÉTERMINÉ":
        print(" Existing writer reusable : YES")
        print(f" Target                   : {canonical_writer}")
    else:
        print(" Existing writer reusable : NO")
        print(" Missing component        : Aucun écrivain de registre automatisé n'injecte les modèles physiques dans registry.json")
    print("================================================================================")

    out = {
        "writers": writers,
        "canonical_writer": canonical_writer,
        "safety": {
            "writes_performed": 0,
            "runtime_mutations": 0
        }
    }
    
    out_file = PROJECT_ROOT / "tools" / "registry_writer_forensics_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()