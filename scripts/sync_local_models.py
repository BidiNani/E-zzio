#!/usr/bin/env python
"""
Synchronise local_registry.py avec les modèles réellement installés via Ollama.

Usage :
    python scripts/sync_local_models.py           # affiche les diffs
    python scripts/sync_local_models.py --check   # exit 1 si désync
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.routing.local_registry import LOCAL_MODELS  # noqa: E402


def get_ollama_models() -> set[str]:
    """Récupère les IDs des modèles installés via `ollama list`."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return set()

    if result.returncode != 0:
        return set()

    lines = result.stdout.strip().splitlines()[1:]  # skip header
    ids = set()
    for line in lines:
        if not line.strip():
            continue
        # Format : NAME  ID  SIZE  MODIFIED
        parts = re.split(r"\s{2,}", line.strip())
        if parts:
            ids.add(parts[0])
    return ids


def main() -> int:
    check_only = "--check" in sys.argv
    installed = get_ollama_models()

    if not installed:
        print("[WARN] Ollama inaccessible — impossible de vérifier")
        return 0

    declared = {m.id for m in LOCAL_MODELS}

    missing_from_registry = installed - declared
    orphan_in_registry = declared - installed

    has_issues = False

    if missing_from_registry:
        has_issues = True
        print(f"\n[MANQUANT] {len(missing_from_registry)} modèle(s) installé(s) mais NON déclaré(s) :")
        for mid in sorted(missing_from_registry):
            print(f"  - {mid}")
        print("  Action : ajouter une LocalModelSpec dans core/routing/local_registry.py")

    if orphan_in_registry:
        has_issues = True
        print(f"\n[ORPHELIN] {len(orphan_in_registry)} modèle(s) déclaré(s) mais PAS installé(s) :")
        for mid in sorted(orphan_in_registry):
            print(f"  - {mid}")
        print("  Action : retirer ou réinstaller (ollama pull <id>)")

    if not has_issues:
        print(f"\n[OK] Registre et Ollama synchronisés ({len(declared)} modèles)")

    if check_only and has_issues:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
