from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def find_consumers(class_name: str) -> list[str]:
    matches = []
    for p in PROJECT_ROOT.glob("**/*.py"):
        if set(p.parts) & EXCLUDED_DIRS:
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            if class_name in content and "agent_provider" not in str(p):
                matches.append(str(p.relative_to(PROJECT_ROOT)))
        except Exception:
            continue
    return matches

def find_modelfiles_or_references(model_tags: list[str]) -> dict[str, list[str]]:
    results = {tag: [] for tag in model_tags}
    for p in PROJECT_ROOT.glob("**/*"):
        if set(p.parts) & EXCLUDED_DIRS or p.is_dir():
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            content_lower = content.lower()
            for tag in model_tags:
                if tag in content_lower:
                    results[tag].append(str(p.relative_to(PROJECT_ROOT)))
        except Exception:
            continue
    return results

def main():
    print("=" * 80)
    print(" GATE v6.45.54 — AGENT PROVIDER CONSUMERS & PHYSICAL MAPPING")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    consumers = find_consumers("AgentProviderAdapter")
    print(f"[1] CONSOMMATEURS ACTIFS DE AgentProviderAdapter ({len(consumers)} trouvés) :")
    for c in consumers:
        print(f"  • {c}")

    tags_to_find = ["ezzio-granite", "ornith-ezzio"]
    physical_map = find_modelfiles_or_references(tags_to_find)
    print("\n[2] PROVENANCE PHYSIQUE DES MODÈLES OLLAMA :")
    for tag, paths in physical_map.items():
        print(f"  • Tag [{tag}] référencé dans {len(paths)} fichiers :")
        for path in paths[:5]:
            print(f"    - {path}")

    report = {
        "consumers": consumers,
        "physical_mapping": physical_map
    }

    out_file = PROJECT_ROOT / "tools" / "gate_v6_45_54_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n[+] Rapport d'arbitrage exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
