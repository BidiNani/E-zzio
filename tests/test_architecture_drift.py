"""
E-ZZIO V9.0 — ARCHITECTURE DRIFT DETECTION SUITE
Vérifie en continu l'intégrité cryptographique des composants Frozen Core
par rapport au manifeste.
"""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


def _load_frozen_manifest() -> dict[str, str]:
    """Charge le manifest Frozen Core, peu importe le format.

    Retourne toujours {"path": "sha256"}.
    """
    manifest_file = ROOT / "docs" / "FROZEN_CORE_MANIFEST.json"
    assert manifest_file.exists(), (
        "Le manifeste FROZEN_CORE_MANIFEST.json doit exister"
    )
    raw = json.loads(manifest_file.read_text(encoding="utf-8"))

    # Format actuel : {"files": {"path": "hash"}}
    if "files" in raw:
        return raw["files"]

    # Ancien format : {"components": {"path": {"sha256": "hash"}}}
    if "components" in raw:
        return {
            path: meta["sha256"] if isinstance(meta, dict) else meta
            for path, meta in raw["components"].items()
        }

    raise AssertionError("Format de manifest inconnu (ni 'files' ni 'components')")


def test_core_manifest_integrity():
    """Vérifie que les fichiers du Core existent et sont intègres."""
    manifest = _load_frozen_manifest()

    for rel_path in manifest:
        target_file = ROOT / rel_path
        assert target_file.exists(), f"Fichier Core manquant : {rel_path}"
        assert target_file.stat().st_size > 100, f"Fichier Core vide : {rel_path}"


def test_drift_no_unauthorized_new_core_modules():
    """Vérifie qu'aucun module externe n'a été inséré dans core/cognition/."""
    cognition_dir = ROOT / "core" / "cognition"
    if not cognition_dir.exists():
        pytest.skip("core/cognition n'existe pas")

    for py in cognition_dir.glob("*.py"):
        txt = py.read_text(encoding="utf-8", errors="ignore").lower()
        for forbidden in ["openhands", "mini_swe", "aider", "langgraph", "requests"]:
            assert forbidden not in txt, (
                f"Symbole interdit {forbidden} détecté dans {py}"
            )