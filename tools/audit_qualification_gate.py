from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_qualification_gate() -> dict[str, Any]:
    gate_path = PROJECT_ROOT / "core" / "models" / "qualification" / "gate.py"
    if not gate_path.exists():
        return {"exists": False}

    try:
        content = gate_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(gate_path))
        lines = content.splitlines()

        functions_source = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = node.lineno - 1
                end = getattr(node, 'end_lineno', start + 40)
                functions_source[node.name] = "\n".join(lines[start:end])

        # Chercher les call-sites de qualify_openai_compatible ou QualificationGate dans toute la codebase
        callsites = []
        for p in PROJECT_ROOT.glob("**/*.py"):
            if set(p.parts) & EXCLUDED_DIRS:
                continue
            try:
                c_content = p.read_text(encoding="utf-8", errors="replace")
                if "qualify_openai_compatible" in c_content or "QualificationGate" in c_content:
                    callsites.append(str(p.relative_to(PROJECT_ROOT)))
            except Exception:
                continue

        return {
            "exists": True,
            "gate_functions": functions_source,
            "callsites": callsites
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}

def main():
    print("=" * 80)
    print(" GATE — QUALIFICATION GATE BRIDGE FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_qualification_gate()

    print("[1] Corps des fonctions de core/models/qualification/gate.py :")
    for fname, src in res.get("gate_functions", {}).items():
        print(f"\n--- Fonction : {fname} ---\n{src}\n")

    print("\n[2] Fichiers faisant référence à qualify_openai_compatible ou QualificationGate :")
    for cs in res.get("callsites", []):
        print(f"  - {cs}")

    print("\n" + "=" * 80)
    print(" BILAN DE L'INSPECTION DU GATE DE QUALIFICATION")
    print("================================================================================")
    print("  - Analyse statique réalisée en lecture seule.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "qualification_gate_inspection_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
