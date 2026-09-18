"""Frozen Core — source de vérité unique pour les fichiers intouchables.

Ce module centralise :
- La liste des fichiers protégés
- Le calcul normalisé des hashes (LF, UTF-8, sans BOM)
- La lecture/écriture du manifest JSON
- La vérification d'intégrité (drift detection)

Tous les tests DOIVENT consommer ce module. Aucun hash hardcodé.
"""
from core.frozen_core.manifest import (
    FROZEN_FILES,
    ManifestDriftError,
    compute_hash,
    load_manifest,
    save_manifest,
    verify_integrity,
)

__all__ = [
    "FROZEN_FILES",
    "load_manifest",
    "save_manifest",
    "compute_hash",
    "verify_integrity",
    "ManifestDriftError",
]
