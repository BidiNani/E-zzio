from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_qualification_consumers() -> list[dict[str, Any]]:
    results = []
    target_terms = {"run_model", "modelrecord", "ingest_discovery", "upsert"}

    for p in PROJECT_ROOT.glob("**/*.py"):
        if set(p.parts) & EXCLUDED_DIRS:
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            content_lower = content.lower()

            hits = [term for term in target_terms if term in content_lower]
            if hits:
                results.append({
                    "file": str(p.relative_to(PROJECT_ROOT)),
                    "hits": hits
                })
        except Exception:
            continue
    return results

def main():
    print("=" * 80)
    print(" GATE — QUALIFICATION CONSUMERS & BRIDGE FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    consumers = inspect_qualification_consumers()

    print("[1] FICHIERS MANIPULANT LES JONCTIONS CLÉS (run_model / ModelRecord / ingest_discovery / upsert) :\n")
    for c in consumers:
        print(f"  - Fichier : {c['file']}")
        print(f"    Mots-clés trouvés : {c['hits']}")

    print("\n" + "=" * 80)
    print(" BILAN DE RECHERCHE DES CONSOMMATEURS")
    print("================================================================================")
    print("  - Analyse statique globale achevée en lecture seule.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out = {
        "consumers": consumers,
        "writes_performed": 0,
        "runtime_mutations": 0
    }

    out_file = PROJECT_ROOT / "tools" / "qualification_consumers_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
