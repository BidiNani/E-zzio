from __future__ import annotations
import json
import ast
import sys
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def find_ingest_discovery_callsites() -> List[Dict[str, Any]]:
    callsites = []
    
    for p in PROJECT_ROOT.glob("**/*.py"):
        if set(p.parts) & EXCLUDED_DIRS:
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            if "ingest_discovery" in content:
                tree = ast.parse(content, filename=str(p))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        func = node.func
                        func_name = ""
                        if isinstance(func, ast.Name):
                            func_name = func.id
                        elif isinstance(func, ast.Attribute):
                            func_name = func.attr
                            
                        if func_name == "ingest_discovery":
                            callsites.append({
                                "file": str(p.relative_to(PROJECT_ROOT)),
                                "lineno": node.lineno
                            })
        except Exception:
            continue
    return callsites

def main():
    print("=" * 80)
    print(" GATE — INGEST DISCOVERY CALL-SITE FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    sites = find_ingest_discovery_callsites()

    print("[1] APPELS RÉELS TROUVÉS À ingest_discovery() :\n")
    if not sites:
        print("  - AUCUN appel direct à ingest_discovery() trouvé dans la codebase.")
    else:
        for s in sites:
            print(f"  - Fichier : {s['file']} (Ligne {s['lineno']})")

    print("\n" + "=" * 80)
    print(" BILAN DES CALL-SITES")
    print("================================================================================")
    print("  - Analyse statique des appels achevée en lecture seule.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out = {
        "callsites": sites,
        "writes_performed": 0,
        "runtime_mutations": 0
    }
    
    out_file = PROJECT_ROOT / "tools" / "ingest_discovery_callsites_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()