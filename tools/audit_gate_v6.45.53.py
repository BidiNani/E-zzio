from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

def inspect_file_content(rel_path: str, keywords: set[str]) -> None:
    p = PROJECT_ROOT / rel_path
    if not p.exists():
        print(f"❌ Fichier introuvable : {rel_path}")
        return

    print(f"\n📁 ANALYSE CIBLÉE : {rel_path}")
    print("-" * 80)
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        for idx, line in enumerate(lines, 1):
            line_lower = line.lower()
            if any(kw in line_lower for kw in keywords):
                print(f"  {idx:04d} | {line}")
    except Exception as e:
        print(f"  ❌ Erreur lecture : {e}")

def main():
    print("=" * 80)
    print(" GATE v6.45.53 — CAPABILITY MAPPING & ROLE PROVENANCE")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    # Cibles prioritaires de traçabilité
    inspect_file_content("core/agent/agent_provider.py", {"ornith", "granite", "local_primary", "provider", "model"})
    inspect_file_content("providers/key_scheduler.py", {"key_pool", "rotate", "gemini", "api_key"})
    inspect_file_content("providers/secrets_loader.py", {"load", "secret", "gemini", "key"})

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
