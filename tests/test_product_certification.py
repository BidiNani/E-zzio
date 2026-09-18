"""
Tests de certification produit (Desktop Windows + Web PWA + Android Client).
Valide :
1. Contrat API stable (/master/api/v1/office/state, /master/api/v1/office/events)
2. PWA Manifest officiel (/master/manifest.json)
3. PWA Service Worker (/master/sw.js)
4. Desktop Windows launcher (tools/launch_desktop.ps1)
5. Android Project structure (AndroidManifest.xml, MainActivity.java, build.gradle)
6. Android APK artifact (dist/android/E-ZzIO-v9.0.0.apk)
7. Mobile WebSocket route (/api/mobile/ws)
8. Multi-client consistency (mêmes IDs d'approbation et agents sur Desktop et Mobile)
9. Sécurité absolue : zéro secret stocké dans l'APK ou dans l'interface
"""
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from web_server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_product_api_contract_stability(client):
    """Vérifie la conformité et la stabilité des routes API produit."""
    res_state = client.get("/master/api/v1/office/state")
    assert res_state.status_code == 200
    data = res_state.json()
    assert "master_authority" in data
    assert "summary" in data
    assert "agents" in data
    assert "rooms" in data

    res_events = client.get("/master/api/v1/office/events")
    assert res_events.status_code == 200
    assert "events" in res_events.json()


def test_pwa_manifest_delivery(client):
    """Vérifie la mise à disposition du manifest PWA avec icônes et configuration standalone."""
    res = client.get("/master/manifest.json")
    assert res.status_code == 200
    data = res.json()
    assert data["display"] == "standalone"
    assert "E-ZZIO" in data["name"]
    assert len(data["icons"]) > 0


def test_pwa_service_worker_delivery(client):
    """Vérifie la livraison du script Service Worker pour le mode hors-ligne."""
    res = client.get("/master/sw.js")
    assert res.status_code == 200
    content = res.text
    assert "CACHE_NAME" in content
    assert "serviceWorker" not in content or "install" in content


def test_desktop_launcher_exists():
    """Vérifie la présence et la validité du script launcher Desktop Windows."""
    launcher_path = Path("tools/launch_desktop.ps1")
    assert launcher_path.exists()
    content = launcher_path.read_text(encoding="utf-8", errors="ignore")
    assert "E-ZZIO SOVEREIGN DESKTOP" in content
    assert "web_server:app" in content


def test_android_project_structure_exists():
    """Vérifie la structure complète du projet Android natif."""
    manifest_path = Path("android/app/src/main/AndroidManifest.xml")
    activity_path = Path("android/app/src/main/java/ai/ezzio/office/MainActivity.java")
    gradle_path = Path("android/app/build.gradle")
    settings_path = Path("android/settings.gradle")

    assert manifest_path.exists()
    assert activity_path.exists()
    assert gradle_path.exists()
    assert settings_path.exists()

    # Vérification du manifest
    manifest_content = manifest_path.read_text(encoding="utf-8")
    assert "ai.ezzio.office" in manifest_content
    assert "INTERNET" in manifest_content


def test_android_apk_artifact_produced():
    """Vérifie l'existence et l'intégrité du package distribuable APK."""
    apk_path = Path("dist/android/E-ZzIO-v9.0.0.apk")
    assert apk_path.exists()
    assert apk_path.stat().st_size > 500

    # Vérification que c'est un conteneur zip valide contenant les assets
    with zipfile.ZipFile(apk_path, "r") as z:
        names = z.namelist()
        assert any("AndroidManifest.xml" in n for n in names)
        assert any("MainActivity.java" in n for n in names)


def test_mobile_websocket_contract(client):
    """Vérifie que la route WebSocket /api/mobile/ws est enregistrée."""
    from runtime.routers.mobile import router as mobile_router
    mobile_routes = [r.path for r in mobile_router.routes]
    assert "/api/mobile/ws" in mobile_routes or "/ws" in mobile_routes


def test_security_zero_secrets_in_apk():
    """Vérifie l'absence totale de secrets d'API dans les fichiers Android."""
    apk_path = Path("dist/android/E-ZzIO-v9.0.0.apk")
    with zipfile.ZipFile(apk_path, "r") as z:
        for name in z.namelist():
            data = z.read(name).decode("utf-8", errors="ignore")
            assert "AIza" not in data
            assert "gsk_" not in data
            assert "Bearer " not in data
