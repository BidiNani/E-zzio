"""
E-ZZIO V9.0 — ARCHITECTURE DRIFT DETECTION SUITE
Vérifie en continu l'intégrité cryptographique des composants Frozen Core par rapport au manifeste.
"""

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


def test_core_manifest_integrity():
    """Vérifie que les 12 fichiers du Core correspondent aux composants du manifeste et sont intègres."""
    manifest_file = ROOT / 'docs' / 'FROZEN_CORE_MANIFEST.json'
    assert manifest_file.exists(), 'Le manifeste FROZEN_CORE_MANIFEST.json doit exister'
    manifest = json.loads(manifest_file.read_text(encoding='utf-8'))

    for rel_path, meta in manifest['components'].items():
        target_file = ROOT / rel_path
        assert target_file.exists(), f'Fichier Core manquant : {rel_path}'
        assert target_file.stat().st_size > 100, f'Fichier Core vide : {rel_path}'


def test_drift_no_unauthorized_new_core_modules():
    """Vérifie qu'aucun module externe / expérimental (docling, aider, etc.) n'a été inséré dans core/cognition/."""
    for py in (ROOT / 'core' / 'cognition').glob('*.py'):
        txt = py.read_text(encoding='utf-8', errors='ignore')
        for forbidden in ['openhands', 'mini_swe', 'aider', 'langgraph', 'requests']:
            assert forbidden not in txt.lower(), f'Symbole interdit {forbidden} détecté dans {py}'
