import socket

import pytest


def _server_up() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 8001), timeout=1.0):
            return True
    except (OSError, ConnectionRefusedError):
        return False


pytestmark = pytest.mark.skipif(
    not _server_up(),
    reason="Serveur E-ZZIO non disponible sur 127.0.0.1:8001",
)


"""Tests d'intégration API pour les endpoints /master/*.

Vérifie que chaque endpoint critique répond correctement et
que le rate limit ne bloque pas les appels légitimes.
"""
import os

import pytest

# Désactive le middleware auth pour les tests
os.environ["EZZIO_DISABLE_AUTH"] = "1"

import httpx

pytestmark = pytest.mark.integration

BASE = "http://127.0.0.1:8001"
TIMEOUT = 5.0


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=TIMEOUT) as c:
        yield c


def _assert_ok(resp, allow_empty=True):
    assert resp.status_code in (200, 204), f"{resp.status_code} {resp.text[:200]}"
    if not allow_empty:
        assert resp.json(), "Réponse vide"


class TestMasterEndpoints:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_ping(self, client):
        r = client.get("/ping")
        assert r.status_code == 200

    def test_metrics(self, client):
        r = client.get("/metrics")
        assert r.status_code == 200

    def test_master_missions(self, client):
        r = client.get("/master/missions")
        _assert_ok(r)

    def test_master_approvals_pending(self, client):
        r = client.get("/master/approvals/pending")
        _assert_ok(r)

    def test_master_providers_health(self, client):
        r = client.get("/master/providers/health")
        _assert_ok(r)

    def test_master_system_diagnostics(self, client):
        r = client.get("/master/system/diagnostics")
        _assert_ok(r)

    def test_master_governance_settings(self, client):
        r = client.get("/master/governance/settings")
        _assert_ok(r)

    def test_routes_debug(self, client):
        r = client.get("/api/_routes")
        assert r.status_code == 200
        data = r.json()
        assert data["count"] > 0


class TestRateLimit:
    """Vérifie que le rate limit n'est pas déclenché sur du polling normal."""

    def test_master_endpoints_not_rate_limited(self, client):
        """3 cycles de polling (30s simulés en rafale) = 9 requêtes max."""
        for _ in range(3):
            for path in ("/master/missions", "/master/approvals/pending", "/master/providers/health"):
                r = client.get(path)
                assert r.status_code != 429, f"{path} renvoie 429"
