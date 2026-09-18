from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_ingest_discovery() -> dict[str, Any]:
    lifecycle_path = PROJECT_ROOT / "core" / "models" / "lifecycle.py"
    if not lifecycle_path.exists():
        return {"exists": False}

    try:
        content = lifecycle_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(lifecycle_path))

        ingest_source = ""
        lines = content.splitlines()

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "ingest_discovery":
                    start_line = node.lineno - 1
                    end_line = getattr(node, 'end_lineno', start_line + 30)
                    ingest_source = "\n".join(lines[start_line:end_line])

        return {
            "exists": True,
            "ingest_source": ingest_source
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}

def main():
    print("=" * 80)
    print(" GATE — INGEST DISCOVERY BODY FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_ingest_discovery()

    print("[1] CORPS DE ModelLifecycleManager.ingest_discovery()")
    print(res.get("ingest_source", "Non trouvé"))

    print("\n" + "=" * 80)
    print(" BILAN DE L'INSPECTION D'INGESTION")
    print("================================================================================")
    print("  - Analyse statique de ingest_discovery() réalisée en lecture seule.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "ingest_discovery_inspection_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
