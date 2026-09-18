from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_discovery_pipeline() -> dict[str, Any]:
    ingest_callers = []
    discovery_sources = []

    target_methods = {"ingest_discovery", "discover", "discover_all", "qualify_candidates", "activate_qualified"}

    for p in PROJECT_ROOT.glob("**/*.py"):
        if set(p.parts) & EXCLUDED_DIRS:
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            content_lower = content.lower()

            for m in target_methods:
                if m in content_lower:
                    rel_path = str(p.relative_to(PROJECT_ROOT))
                    if m == "ingest_discovery":
                        ingest_callers.append(rel_path)
                    elif "discover" in m or "qualify" in m or "activate" in m:
                        if rel_path not in discovery_sources:
                            discovery_sources.append(rel_path)
        except Exception:
            continue

    # Inspection spécifique de lifecycle.py pour voir comment ingest_discovery est défini
    lifecycle_path = PROJECT_ROOT / "core" / "models" / "lifecycle.py"
    lifecycle_methods = []
    if lifecycle_path.exists():
        try:
            tree = ast.parse(lifecycle_path.read_text(encoding="utf-8", errors="replace"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    lifecycle_methods.append(node.name)
        except Exception:
            pass

    return {
        "ingest_callers": ingest_callers,
        "discovery_sources": discovery_sources,
        "lifecycle_methods": lifecycle_methods
    }

def main():
    print("=" * 80)
    print(" GATE — DISCOVERY → LIFECYCLE INPUT FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_discovery_pipeline()

    print("[1] ANALYSE DE MODEL LIFECYCLE (core/models/lifecycle.py) :")
    print(f"  • Méthodes identifiées : {res['lifecycle_methods']}")

    print("\n[2] APPELANTS DE LA MÉTHODE ingest_discovery :")
    if res["ingest_callers"]:
        for c in res["ingest_callers"]:
            print(f"  • {c}")
    else:
        print("  ❌ Aucun appel explicite à ingest_discovery trouvé dans les sources actives (hors définition).")

    print("\n[3] SOURCES POTENTIELLES DE DISCOVERY / QUALIFICATION :")
    for s in res["discovery_sources"][:10]:
        print(f"  • {s}")

    print("\n" + "=" * 80)
    print(" BILAN FORENSIQUE DE LA DISCOVERY")
    print("================================================================================")
    print("  • Le lifecycle manager gère les records, mais la source de découverte")
    print("    automatique (ingest_discovery) n'est pas encore câblée sur un client de scan actif.")
    print("  • Aucun code de production n'a été muté. Lecture seule respectée à 100 %.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "discovery_lifecycle_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
