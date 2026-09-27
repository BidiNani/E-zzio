"""
Test de bout en bout du middleware d'authentification de web_server.py.

Verifie les comportements :
  1. cle absente  -> /master/* reste ouvert (comportement de dev preserve)
  2. cle presente -> /master/* exige X-API-Key (401 sans, OK avec)
  3. /api/v1/webhook/n8n est fail-closed et refuse l'ancienne cle publique

Le point 3 est le correctif de securite : avant, ce routeur avait
`os.getenv("EZZIO_API_KEY", "ezzio_secret_key_local_dev")` — une cle
publique en dur.
"""

import importlib
import sys
import warnings

import pytest
from fastapi.testclient import TestClient

ROOT = r"G:\AI\E-zzio"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _reload_server(monkeypatch, key: str | None, disable_auth: str = "0"):
    """Recharge web_server avec un environnement d'auth controle."""
    for var in ("EZZIO_API_KEY", "EZZIO_DISABLE_AUTH"):
        monkeypatch.delenv(var, raising=False)
    if key is not None:
        monkeypatch.setenv("EZZIO_API_KEY", key)
    monkeypatch.setenv("EZZIO_DISABLE_AUTH", disable_auth)

    sys.modules.pop("web_server", None)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return importlib.import_module("web_server")


@pytest.fixture
def client_factory(monkeypatch):
    def _make(key=None, disable_auth="0"):
        mod = _reload_server(monkeypatch, key, disable_auth)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return TestClient(mod.app)

    return _make


PROTECTED = "/master/system/diagnostics"
PUBLIC = "/health"
WEBHOOK = "/api/v1/webhook/n8n"


class TestPublicPathsNeverRequireKey:
    def test_health_is_public_even_with_a_key_set(self, client_factory):
        c = client_factory(key="une-cle-solide")
        assert c.get(PUBLIC).status_code in (200, 503)


class TestDevBehaviourPreserved:
    """Pas de cle = mode dev. Ne pas casser les tests ni le dev local."""

    def test_protected_route_open_when_no_key(self, client_factory):
        c = client_factory(key=None)
        assert c.get(PROTECTED).status_code != 401

    def test_disable_auth_flag_bypasses_everything(self, client_factory):
        c = client_factory(key="une-cle-solide", disable_auth="1")
        assert c.get(PROTECTED).status_code != 401


class TestKeyEnforcedWhenConfigured:
    def test_missing_header_is_401(self, client_factory):
        c = client_factory(key="une-cle-solide-aleatoire")
        assert c.get(PROTECTED).status_code == 401

    def test_wrong_key_is_401(self, client_factory):
        c = client_factory(key="une-cle-solide-aleatoire")
        r = c.get(PROTECTED, headers={"X-API-Key": "mauvaise"})
        assert r.status_code == 401

    def test_correct_key_passes(self, client_factory):
        c = client_factory(key="une-cle-solide-aleatoire")
        r = c.get(PROTECTED, headers={"X-API-Key": "une-cle-solide-aleatoire"})
        assert r.status_code != 401

    def test_public_default_key_is_refused(self, client_factory):
        """L'ancienne cle publique en dur ne doit plus fonctionner."""
        c = client_factory(key="ezzio_secret_key_local_dev")
        r = c.get(PROTECTED, headers={"X-API-Key": "ezzio_secret_key_local_dev"})
        assert r.status_code == 401


class TestRouterLevelFailClosed:
    """Le webhook est monte dans web_server.py : surface reellement exposee.

    `routers.stats` et `routers.system` ne sont pas enregistres (404 sur
    l'entree de production). Ils restent corriges par defense en profondeur :
    un `include_router` futur les rendrait accessibles.
    """

    def test_webhook_refused_without_configured_key(self, client_factory):
        c = client_factory(key=None)
        r = c.post(WEBHOOK, json={"intent": "x", "response": "y"})
        assert r.status_code == 403

    def test_webhook_refused_with_public_default_key(self, client_factory):
        """Avant correction : la cle publique en dur suffisait."""
        c = client_factory(key="ezzio_secret_key_local_dev")
        r = c.post(
            WEBHOOK,
            json={"intent": "x", "response": "y"},
            headers={"X-API-Key": "ezzio_secret_key_local_dev"},
        )
        assert r.status_code == 403

    def test_webhook_refused_with_wrong_key(self, client_factory):
        c = client_factory(key="une-cle-solide-aleatoire")
        r = c.post(
            WEBHOOK,
            json={"intent": "x", "response": "y"},
            headers={"X-API-Key": "mauvaise"},
        )
        assert r.status_code == 403

    def test_stats_and_system_not_exposed_by_production_app(self, client_factory):
        # 404 attendu : ces routeurs ne sont pas montes. Documente
        # deliberement que leur surface n'est pas atteignable aujourd'hui.
        c = client_factory(key=None)
        assert c.get("/api/v1/stats").status_code == 404
        assert c.post("/api/v1/system/cleanup", json={"dry_run": True}).status_code == 404


class TestCorrelationIdUnchanged:
    def test_correlation_id_header_still_present(self, client_factory):
        c = client_factory(key=None)
        r = c.get(PUBLIC)
        assert "X-Correlation-ID" in r.headers

    def test_client_correlation_id_is_echoed(self, client_factory):
        c = client_factory(key=None)
        r = c.get(PUBLIC, headers={"X-Correlation-ID": "trace-123"})
        assert r.headers.get("X-Correlation-ID") == "trace-123"
