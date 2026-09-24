# tests/conftest.py - Fixtures partagees
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Charge EZZIO_API_KEY depuis .env (comme le fait le serveur au demarrage)
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass  # python-dotenv pas installe, on continue


@pytest.fixture
def client():
    """TestClient authentifie via X-API-Key (valeur lue depuis .env)."""
    from web_server import app

    api_key = os.getenv("EZZIO_API_KEY", "")
    test_client = TestClient(app)
    if api_key:
        test_client.headers.update({"X-API-Key": api_key})
    return test_client

# FIX-FLAKY : nettoyage d'etat entre tests pour eviter les fuites
# (event loop, patches, sys.modules). Certains tests laissent un etat
# qui casse les tests suivants quand on lance tests/unit/ en entier.
import asyncio
import gc
import sys

import pytest


@pytest.fixture(autouse=True)
def _clean_state_between_tests():
    """Nettoie l'etat partage entre chaque test (evite flaky)."""
    yield
    # 1. Fermer les event loops orphelines
    try:
        loop = asyncio.get_event_loop_policy().get_event_loop()
        if loop and not loop.is_closed() and not loop.is_running():
            loop.close()
    except Exception:
        pass

    # 2. Forcer un GC pour nettoyer les references
    gc.collect()

# ============================================================
# STABILISATION ENV — cv2/numpy (import unique)
# ============================================================
import sys as _sys


def _stabilize_native_modules():
    """Force l'import unique de cv2/numpy au debut de la session pytest.

    Sans cela, un test qui recharge numpy (via importlib.reload)
    provoque 'cannot load module more than once per process' pour cv2.
    """
    if "cv2" in _sys.modules and "numpy" in _sys.modules:
        return
    try:
        import cv2  # noqa: F401
        import numpy  # noqa: F401
    except ImportError:
        # OpenCV/numpy absents : les tests concernes seront skip
        pass


# Import au chargement de conftest = avant tous les tests
_stabilize_native_modules()
