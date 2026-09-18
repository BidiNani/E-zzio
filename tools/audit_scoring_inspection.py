from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_scoring_and_calls() -> dict[str, Any]:
    scoring_path = PROJECT_ROOT / "core" / "models" / "scoring.py"
    if not scoring_path.exists():
        return {"exists": False}

    try:
        content = scoring_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(scoring_path))
        lines = content.splitlines()

        functions_source = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = node.lineno - 1
                end = getattr(node, 'end_lineno', start + 30)
                functions_source[node.name] = "\n".join(lines[start:end])

        # Chercher aussi les call-sites de classify_tier ou calculate_score dans toute la codebase
        callsites = []
        for p in PROJECT_ROOT.glob("**/*.py"):
            if set(p.parts) & EXCLUDED_DIRS:
                continue
            try:
                c_content = p.read_text(encoding="utf-8", errors="replace")
                if "classify_tier" in c_content or "calculate_score" in c_content:
                    callsites.append(str(p.relative_to(PROJECT_ROOT)))
            except Exception:
                continue

        return {
            "exists": True,
            "scoring_functions": functions_source,
            "callsites": callsites
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}

def main():
    print("=" * 80)
    print(" GATE — SCORING TIER ENGINE & CALL-SITES FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_scoring_and_calls()

    print("[1] Corps des fonctions de core/models/scoring.py :")
    for fname, src in res.get("scoring_functions", {}).items():
        print(f"\n--- Fonction : {fname} ---\n{src}\n")

    print("\n[2] Fichiers faisant référence à classify_tier ou calculate_score :")
    for cs in res.get("callsites", []):
        print(f"  - {cs}")

    print("\n" + "=" * 80)
    print(" BILAN DE L'INSPECTION DU MOTEUR DE SCORE / TIER")
    print("================================================================================")
    print("  - Analyse statique réalisée en lecture seule.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "scoring_inspection_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
