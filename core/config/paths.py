"""Ancrage racine de l'écosystème E-zzio — résolution dynamique.

Point d'ancrage unique pour tous les chemins de projet. Remplace les
chemins absolus codés en dur (G:\\AI\\E-zzio) qui rendaient l'écosystème
dépendant d'un emplacement de clone : dans un worktree, le dépôt est
checkout ailleurs et les modules écrivaint hors de leur arbre.

Ordre de priorité de get_project_root() :
  1. Variable d'environnement EZZIO_ROOT, puis EZZIO_PROJECT_DIR.
  2. Découverte ascendante depuis ce fichier, via un marqueur de dépôt
     fiable (.git en répertoire pour un clone normal, .git en fichier pour
     un worktree ou un sous-module, pyproject.toml, pytest.ini).
  3. Repli passif sur l'emplacement historique, pour compatibilité
     ascendante quand aucun contexte ne permet de trancher.

Le résultat est mis en cache : la découverte fait plusieurs accès disque
et la racine ne change pas pendant une session.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

__all__ = [
    "get_project_root",
    "get_project_root_str",
    "resolve_path",
    "ROOT_MARKERS",
]

# Marqueurs envoyés pour identifier la racine d'un dépôt, du plus au moins
# spécifique. .git est prioritaire : il identifie un dépôt même sans
# pyproject.toml (worktree, clone minimal).
ROOT_MARKERS: tuple[str, ...] = (".git", "pyproject.toml", "pytest.ini")

# Emplacement historique, utilisé uniquement en dernier recours.
LEGACY_FALLBACK = "G:/AI/E-zzio"

# Variables d'environnement consultées, dans l'ordre.
ROOT_ENV_VARS: tuple[str, ...] = ("EZZIO_ROOT", "EZZIO_PROJECT_DIR")


def _from_env() -> Path | None:
    """Racine fournie explicitement par l'environnement, si elle est valide."""
    for var in ROOT_ENV_VARS:
        raw = os.environ.get(var)
        if not raw or not raw.strip():
            continue
        candidate = Path(raw).expanduser()
        if candidate.is_dir():
            return candidate.resolve()
    return None


def _discover(start: Path) -> Path | None:
    """Remonte depuis start jusqu'à trouver un marqueur de dépôt."""
    for candidate in (start, *start.parents):
        for marker in ROOT_MARKERS:
            # .git peut être un répertoire (clone) ou un fichier (worktree).
            if (candidate / marker).exists():
                return candidate
    return None


@lru_cache(maxsize=1)
def get_project_root() -> Path:
    """Racine absolue du projet E-zzio, résolue une fois et mémorisée."""
    env_root = _from_env()
    if env_root is not None:
        return env_root

    discovered = _discover(Path(__file__).resolve().parent)
    if discovered is not None:
        return discovered

    return Path(LEGACY_FALLBACK).resolve()


def get_project_root_str() -> str:
    """Racine du projet sous forme de chaîne.

    Les modules de production consomment la racine via os.path.join et
    os.path.abspath, qui attendent une chaîne : ce helper évite de
    LIABILITY convertir un Path à chaque appel.
    """
    return str(get_project_root())


def resolve_path(*parts: str | os.PathLike[str]) -> Path:
    """Construit un chemin absolu sous la racine du projet."""
    return get_project_root().joinpath(*parts)
