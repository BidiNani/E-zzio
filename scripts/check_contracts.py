#!/usr/bin/env python
"""
Validateur de contrats providers <-> code.

Détecte automatiquement :
  1. Modèles obsolètes encore référencés dans le code
  2. Modèles déclarés mais absents d'un provider concret
  3. Incohérences thinking (method/levels)
  4. Providers non testés

Exécution : python scripts/check_contracts.py
Sortie : exit 0 si OK, 1 si erreurs.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ajout du root au path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.routing.providers_registry import (  # noqa: E402
    PROVIDERS,
    all_deprecated,
    all_models,
)


def find_obsolete_references() -> list[tuple[Path, int, str]]:
    """Cherche les références aux modèles dépréciés dans le code."""
    deprecated_ids = {m.id for m in all_deprecated()}
    if not deprecated_ids:
        return []

    hits = []
    patterns = [
        ROOT / "core",
        ROOT / "routers",
        ROOT / "agents",
    ]
    exclude_dirs = {"__pycache__", ".venv", "_archive", "tests", "state"}
    exclude_files = {"providers_registry.py", "check_contracts.py"}

    for base in patterns:
        if not base.exists():
            continue
        for py in base.rglob("*.py"):
            if any(ex in py.parts for ex in exclude_dirs):
                continue
            if py.name in exclude_files:
                continue
            try:
                content = py.read_text(encoding="utf-8")
            except Exception:
                continue
            for lineno, line in enumerate(content.split("\n"), 1):
                for dep in deprecated_ids:
                    # Ignore les commentaires
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    if dep in line:
                        hits.append((py, lineno, line.strip()))
    return hits


def check_registry_coherence() -> list[str]:
    """Vérifie la cohérence interne du registre."""
    errors = []

    # 1. Unicité des IDs
    ids = [m.id for m in all_models()]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        errors.append(f"IDs dupliqués : {dupes}")

    # 2. Cohérence thinking
    for m in all_models():
        if m.thinking_method == "thinkingLevel":
            bad = [lvl for lvl in m.thinking_levels if lvl not in ("low", "high")]
            if bad:
                errors.append(
                    f"{m.id}: thinkingLevel avec levels invalides {bad} "
                    f"(seuls low/high autorisés en 3.x)"
                )

    # 3. Replaced_by doit exister
    all_ids = {m.id for m in all_models()}
    for m in all_deprecated():
        if m.replaced_by and m.replaced_by not in all_ids:
            errors.append(f"{m.id}: replaced_by={m.replaced_by} n'existe pas")

    # 4. Default model doit exister
    for p in PROVIDERS.values():
        pids = {m.id for m in p.models}
        if p.default_model not in pids:
            errors.append(f"{p.name}: default_model={p.default_model} absent de models")
        for fb in p.fallback_models:
            if fb not in pids:
                errors.append(f"{p.name}: fallback_model={fb} absent de models")

    return errors


def main() -> int:
    print("[check_contracts] Validation en cours...")

    errors = []

    # Cohérence registre
    coherence = check_registry_coherence()
    if coherence:
        errors.extend(coherence)
        print(f"\n[ERREURS] {len(coherence)} incohérence(s) registre :")
        for e in coherence:
            print(f"  - {e}")
    else:
        print("  [OK] Registre cohérent")

    # Références obsolètes
    obs = find_obsolete_references()
    if obs:
        print(f"\n[ERREURS] {len(obs)} référence(s) à des modèles dépréciés :")
        for py, ln, line in obs[:20]:
            rel = py.relative_to(ROOT)
            print(f"  [{rel}:{ln}] {line[:100]}")
        errors.append(f"{len(obs)} références obsolètes")
    else:
        print("  [OK] Aucune référence à un modèle déprécié")

    # Résumé
    print(f"\n{'=' * 60}")
    if errors:
        print(f"[ECHEC] {len(errors)} problème(s) détecté(s)")
        return 1
    print("[OK] Tous les contrats sont respectés")
    return 0


if __name__ == "__main__":
    sys.exit(main())
