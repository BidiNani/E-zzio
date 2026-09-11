from __future__ import annotations
import ast
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def scan_provenance(keywords: set[str]) -> Dict[str, List[str]]:
    matches = {kw: [] for kw in keywords}
    for p in PROJECT_ROOT.glob("**/*.py"):
        if set(p.parts) & EXCLUDED_DIRS:
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            content_lower = content.lower()
            for kw in keywords:
                if kw in content_lower:
                    matches[kw].append(str(p.relative_to(PROJECT_ROOT)))
        except Exception:
            continue
    return matches

def main():
    print("=" * 80)
    print(" GATE v6.45.52 — GEMINI & OLLAMA PROVENANCE TRACING")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    gemini_keywords = {"gemini", "rotate_key", "key_pool", "api_key", "rotation"}
    ollama_keywords = {"granite", "ornith", "ollama", "local_primary", "127.0.0.1:11434"}

    print("[1] PROVENANCE CLOUD (Gemini / Clés) :")
    gemini_res = scan_provenance(gemini_keywords)
    for kw, paths in gemini_res.items():
        print(f"  • Mot-clé [{kw}] détecté dans {len(paths)} fichiers actifs :")
        for path in paths[:5]:
            print(f"    - {path}")

    print("\n[2] PROVENANCE LOCALE (Ollama / Granite / Ornith) :")
    ollama_res = scan_provenance(ollama_keywords)
    for kw, paths in ollama_res.items():
        print(f"  • Mot-clé [{kw}] détecté dans {len(paths)} fichiers actifs :")
        for path in paths[:5]:
            print(f"    - {path}")

    report = {
        "gemini_provenance": gemini_res,
        "ollama_provenance": ollama_res
    }
    
    out_file = PROJECT_ROOT / "tools" / "gate_v6_45_52_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n[+] Rapport de provenance exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()