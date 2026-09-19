from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_ollama_sync() -> dict[str, Any]:
    # Chercher des fichiers liés à ollama dans le projet
    ollama_files = []
    for p in PROJECT_ROOT.glob("**/*ollama*.py"):
        if set(p.parts) & EXCLUDED_DIRS:
            continue
        ollama_files.append(p)

    results = {}
    for path in ollama_files:
        rel_path = str(path.relative_to(PROJECT_ROOT))
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=str(path))

            functions = []
            classes = []
            calls_to_ingest = "ingest" in content or "lifecycle" in content

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)

            results[rel_path] = {
                "classes": classes,
                "functions": functions,
                "mentions_ingest_or_lifecycle": calls_to_ingest,
                "content_sample": content[:500]
            }
        except Exception as e:
            results[rel_path] = {"error": str(e)}

    return results

def main():
    print("=" * 80)
    print(" GATE — OLLAMA SYNC & DISCOVERY PRODUCER FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_ollama_sync()

    if not res:
        print("  - Aucun fichier contenant 'ollama' trouvé dans la codebase.")
    else:
        for file_path, details in res.items():
            print(f"[FICHIER] {file_path}")
            print(f"  - Classes : {details.get('classes', [])}")
            print(f"  - Fonctions : {details.get('functions', [])}")
            print(f"  - Mentionne ingest/lifecycle : {details.get('mentions_ingest_or_lifecycle', False)}")
            print()

    print("=" * 80)
    print(" BILAN DE L'INSPECTION OLLAMA SYNC")
    print("================================================================================")
    print("  - Analyse statique réalisée en lecture seule.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "ollama_sync_inspection_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
