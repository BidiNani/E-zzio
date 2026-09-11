from __future__ import annotations
import json
import ast
import sys
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_fabric_discovery_block() -> Dict[str, Any]:
    fabric_path = PROJECT_ROOT / "core" / "models" / "fabric.py"
    if not fabric_path.exists():
        return {"exists": False}
    
    try:
        content = fabric_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        
        # Trouver la ligne contenant ingest_discovery ou result = ingest
        target_indices = []
        for idx, line in enumerate(lines):
            if "ingest_discovery" in line or "result = ingest" in line:
                target_indices.append(idx)
                
        snippets = []
        for idx in target_indices:
            start = max(0, idx - 10)
            end = min(len(lines), idx + 15)
            snippets.append({
                "line_number": idx + 1,
                "snippet": "\n".join(lines[start:end])
            })
            
        return {
            "exists": True,
            "snippets": snippets
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}

def main():
    print("=" * 80)
    print(" GATE — FABRIC DISCOVERY BLOCK FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_fabric_discovery_block()

    for s in res.get("snippets", []):
        print(f"--- Extrait autour de la ligne {s['line_number']} ---\n{s['snippet']}\n")

    print("\n" + "=" * 80)
    print(" BILAN DE L'INSPECTION DU BLOC DE DÉCOUVERTE")
    print("================================================================================")
    print("  - Analyse statique réalisée en lecture seule.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "fabric_discovery_block_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()