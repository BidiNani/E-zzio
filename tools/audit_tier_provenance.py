from __future__ import annotations
import json
import ast
import sys
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_tier_assignment() -> Dict[str, Any]:
    tier_terms = {"FAST", "MID", "HEAVY", "SPECIALIZED", "UNQUALIFIED"}
    results = {}
    
    for p in PROJECT_ROOT.glob("**/*.py"):
        if set(p.parts) & EXCLUDED_DIRS:
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            found_terms = [t for t in tier_terms if t in content]
            if found_terms or "tier" in content.lower():
                tree = ast.parse(content, filename=str(p))
                functions_or_methods = []
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        functions_or_methods.append(node.name)
                        
                results[str(p.relative_to(PROJECT_ROOT))] = {
                    "matched_terms": found_terms,
                    "functions": functions_or_methods
                }
        except Exception as e:
            results[str(p.relative_to(PROJECT_ROOT))] = {"error": str(e)}
            
    return results

def main():
    print("=" * 80)
    print(" GATE — TIER PROVENANCE FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_tier_assignment()

    print(f"[1] Fichiers faisant référence aux tiers ou à 'tier' ({len(res)} fichiers trouvés) :\n")
    for file_path, details in res.items():
        print(f"  - {file_path}")
        print(f"    Termes : {details.get('matched_terms', [])}")
        print(f"    Fonctions : {details.get('functions', [])[:5]} ...")

    print("\n" + "=" * 80)
    print(" BILAN DE L'INSPECTION DES TIERS")
    print("================================================================================")
    print("  - Analyse statique réalisée en lecture seule.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "tier_provenance_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()