from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_ingest_usage_in_fabric() -> dict[str, Any]:
    fabric_path = PROJECT_ROOT / "core" / "models" / "fabric.py"
    lifecycle_path = PROJECT_ROOT / "core" / "models" / "lifecycle.py"

    results = {}

    for path, name in [(fabric_path, "fabric"), (lifecycle_path, "lifecycle")]:
        if not path.exists():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=str(path))

            snippets = []
            lines = content.splitlines()

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    func_name = ""
                    if isinstance(func, ast.Name):
                        func_name = func.id
                    elif isinstance(func, ast.Attribute):
                        func_name = func.attr

                    if "ingest" in func_name.lower():
                        start_line = max(0, node.lineno - 3)
                        end_line = min(len(lines), getattr(node, 'end_lineno', node.lineno + 3))
                        snippet = "\n".join(lines[start_line:end_line])
                        snippets.append({
                            "func_name": func_name,
                            "lineno": node.lineno,
                            "snippet": snippet
                        })
            results[name] = snippets
        except Exception as e:
            results[name] = {"error": str(e)}

    return results

def main():
    print("=" * 80)
    print(" GATE — FABRIC TO LIFECYCLE INGEST EXACT CALL-SITE FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_ingest_usage_in_fabric()

    for file_key, items in res.items():
        print(f"[FICHIER] core/models/{file_key}.py")
        if isinstance(items, list):
            if not items:
                print("  - Aucun appel contenant 'ingest' trouvé.")
            for item in items:
                print(f"  -> Fonction/Attribut : {item['func_name']} (Ligne {item['lineno']})")
                print(f"     Extrait :\n{item['snippet']}\n")
        else:
            print(f"  - Erreur : {items.get('error')}")

    print("\n" + "=" * 80)
    print(" BILAN DE L'INSPECTION DE L'INGESTION INDIRECTE")
    print("================================================================================")
    print("  - Analyse statique des appels 'ingest' menée en lecture seule.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "fabric_ingest_inspection_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
