# FIX-NUMPY-CV2 v2 : precharger cv2 EN PREMIER (il charge numpy en interne
# proprement). Ensuite numpy est deja dans sys.modules -> no-op.
# Bug corrige : Pillow recent + numpy 2.x + cv2 provoquent
# "ImportError: cannot load module more than once per process".
try:
    import cv2  # noqa: F401
except ImportError:
    pass

import numpy  # noqa: F401

# FIX-NUMPY-CV2 : pre-charger numpy et cv2 AVANT tout autre import
# Raison : Pillow recent + numpy 2.x + cv2 provoquent "cannot load module more than once"
# Reference : interaction connue entre ces 3 packages, fix par prechargement force.
try:
    import cv2  # noqa: F401
except ImportError:
    pass  # cv2 optionnel
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
