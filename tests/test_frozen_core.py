"""Gate unique Frozen Core — remplace tous les hashes hardcodés.

Toute vérification d'intégrité Frozen Core DOIT passer par ce test.
Les autres tests (ex: v9.4) importent core.frozen_core.verify_integrity.
"""
import pytest

from core.frozen_core import FROZEN_FILES, ManifestDriftError, verify_integrity


def test_frozen_core_integrity():
    """Vérifie qu'aucun fichier Frozen Core n'a dérivé."""
    try:
        verify_integrity()
    except ManifestDriftError as e:
        pytest.fail(str(e))


def test_frozen_core_files_exist():
    """Vérifie que tous les fichiers déclarés existent."""
    from pathlib import Path

    from core.frozen_core.manifest import REPO_ROOT
    missing = [rel for rel in FROZEN_FILES if not (REPO_ROOT / rel).exists()]
    assert not missing, f"Fichiers Frozen Core manquants : {missing}"


def test_frozen_core_manifest_is_synced():
    """Vérifie que le manifest ne contient que des fichiers déclarés."""
    from core.frozen_core import load_manifest
    manifest = load_manifest()
    manifest_files = set(manifest.get("files", {}).keys())
    declared = set(FROZEN_FILES)
    extra = manifest_files - declared
    missing = declared - manifest_files
    assert not extra, f"Manifest contient des fichiers non déclarés : {extra}"
    assert not missing, f"Manifest manque des fichiers déclarés : {missing}"
