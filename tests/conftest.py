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
