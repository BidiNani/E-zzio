from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_discovery_producers() -> list[dict[str, Any]]:
    results = []
    ollama_patterns = {"/api/tags", "/api/ps", "ollama.list", "ollama", "list_models", "models.list"}
    gemini_patterns = {"key_vault", "key_pool", "key_scheduler", "secrets_loader", "gemini"}

    for p in PROJECT_ROOT.glob("**/*.py"):
        if set(p.parts) & EXCLUDED_DIRS:
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            content_lower = content.lower()

            has_ollama = any(op in content_lower for op in ollama_patterns)
            has_gemini = any(gp in content_lower for gp in gemini_patterns)
            has_discover = "discover" in content_lower or "scan" in content_lower or "detect" in content_lower

            if (has_ollama or has_gemini) and has_discover:
                rel_path = str(p.relative_to(PROJECT_ROOT))
                results.append({
                    "file": rel_path,
                    "has_ollama_discovery": has_ollama,
                    "has_gemini_discovery": has_gemini,
                    "has_discover_keyword": has_discover
                })
        except Exception:
            continue
    return results

def main():
    print("=" * 80)
    print(" GATE — DISCOVERY PRODUCER FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    producers = inspect_discovery_producers()

    print("[PRODUCERS] Recherche de producteurs de discovery (Ollama/Gemini) :\n")
    if producers:
        for pr in producers:
            print(f"  • Fichier : {pr['file']}")
            print(f"    - Détection Ollama : {'YES' if pr['has_ollama_discovery'] else 'NO'}")
            print(f"    - Détection Gemini : {'YES' if pr['has_gemini_discovery'] else 'NO'}")
            print(f"    - Mots-clés discovery : {'YES' if pr['has_discover_keyword'] else 'NO'}")
            print("")
    else:
        print("  ❌ Aucun producteur de discovery explicite combinant scan et API n'a été trouvé.")

    print("--------------------------------------------------------------------------------")
    print(" [VERDICT]")
    print(f" Discovery Producer Existant : {'OUI (Voir liste ci-dessus)' if producers else 'NON (Le maillon est absent)'}")
    print("================================================================================")

    out = {
        "producers": producers,
        "writes_performed": 0,
        "runtime_mutations": 0
    }

    out_file = PROJECT_ROOT / "tools" / "discovery_producer_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
