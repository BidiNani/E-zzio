"""
Tests de validation produit E-ZZIO V9.0 : Mode Hors-Ligne, Provenance des Assets et Dépendances.
Valide :
1. Mode hors-ligne : résilience du Service Worker et de l'interface sans accès externe
2. Provenance des assets : conformité ASSET_LICENSES.json et absence de contenu tiers protégé
3. Gouvernance des dépendances : conformité DEPENDENCIES.md
4. Sécurité globale : non-exposition des secrets dans les logs, le terminal et les événements
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from web_server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_offline_ui_service_worker_contract(client):
    """Vérifie que le Service Worker fournit le cache hors-ligne pour la racine et le manifest."""
    res_sw = client.get("/master/sw.js")
    assert res_sw.status_code == 200
    sw_code = res_sw.text
    assert "CACHE_NAME" in sw_code
    assert "ASSETS_TO_CACHE" in sw_code
    assert "offline: true" in sw_code


def test_offline_font_stack_resilience():
    """Vérifie que l'interface HTML inclut des polices système de secours pour fonctionner sans Internet."""
    html_path = Path("runtime/web/index.html")
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")
    assert "system-ui" in content
    assert "ui-monospace" in content
    assert "offline-indicator" in content
    assert "ezzio_cached_state" in content


def test_asset_licenses_manifest_integrity():
    """Vérifie l'existence et la validité du manifeste de licences d'assets graphiques."""
    manifest_path = Path("assets/ASSET_LICENSES.json")
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["version"] == "9.0.0"
    assert "prohibited_franchises" in data
    assert "The Escapists" in data["prohibited_franchises"]
    assert "The Office" in data["prohibited_franchises"]
    assert len(data["assets"]) >= 3
    for a in data["assets"]:
        assert "asset_id" in a
        assert "license" in a
        assert a.get("verified") is True


def test_icon_svg_exists_and_valid():
    """Vérifie la présence et la validité de l'icône vectorielle officielle du produit."""
    icon_path = Path("assets/ui/icon.svg")
    assert icon_path.exists()
    svg = icon_path.read_text(encoding="utf-8")
    assert "<svg" in svg
    assert "E-ZZIO" in svg
    assert "SOVEREIGN V9.0" in svg


def test_dependencies_documentation_integrity():
    """Vérifie l'existence du document de référence des dépendances."""
    dep_path = Path("docs/DEPENDENCIES.md")
    assert dep_path.exists()
    content = dep_path.read_text(encoding="utf-8")
    assert "FastAPI" in content
    assert "Pydantic" in content
    assert "Uvicorn" in content
    assert "Frozen Core" in content or "Phase AL" in content


def test_terminal_logs_scrub_secrets(client):
    """Vérifie que les logs de terminal d'agent ne contiennent aucun secret sensible."""
    res = client.get("/master/api/v1/office/state")
    assert res.status_code == 200
    agents = res.json()["agents"]
    for a in agents:
        logs = a.get("terminal_logs", [])
        for log_line in logs:
            assert "AIza" not in log_line
            assert "gsk_" not in log_line
            assert "Bearer" not in log_line
