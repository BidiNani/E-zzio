#!/usr/bin/env python
"""
Synchronise local_registry.py avec les modèles réellement installés via Ollama.

Usage :
    python scripts/sync_local_models.py           # affiche les diffs
    python scripts/sync_local_models.py --check   # exit 1 si désync
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.routing.local_registry import LOCAL_MODELS  # noqa: E402


def get_ollama_models() -> set[str]:
    """Récupère les IDs des modèles installés.

    Essaie dans l'ordre :
      1. CLI `ollama list` (rapide)
      2. API HTTP (fallback si CLI KO)
    Respecte OLLAMA_HOST si défini.
    """
    # Tentative 1 : CLI
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().splitlines()[1:]
            ids = set()
            for line in lines:
                if not line.strip():
                    continue
                parts = re.split(r"\s{2,}", line.strip())
                if parts:
                    ids.add(parts[0])
            if ids:
                return ids
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Tentative 2 : API HTTP
    try:
        host = os.environ.get("OLLAMA_HOST", "").strip()
        # 0.0.0.0 est un BIND, pas une adresse de connexion
        if not host or host.startswith(("0.0.0.0", "::")):
            host = "http://localhost:11434"
        elif not host.startswith("http"):
            host = f"http://{host}"
        url = f"{host}/api/tags"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {m["name"] for m in data.get("models", [])}
    except Exception:
        return set()


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
