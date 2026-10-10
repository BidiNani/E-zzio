"""
Regression — classification d'authentification explicite des surfaces /api.

Contexte :
    web_server.py ne protegeait que /master/*, /api/accounts/* et
    /api/models/select. Les surfaces /api sensibles (exploration de fichiers,
    etat, automatisations, kill switch, config UI) restaient accessibles SANS
    cle des qu'EZZIO_API_KEY etait configuree.

Ces tests verrouillent la classification :
    PUBLIC        -> /health (jamais 401)
    AUTHENTICATED -> /api/files, /api/memory, /api/automations, /api/kill,
                     /api/missions, /api/projects, /api/objectives,
                     /api/approvals, /api/settings
    PRIVILEGED    -> /master/*, /api/accounts/*, /api/models/select

Le mode dev (aucune EZZIO_API_KEY) est preserve : les routes restent ouvertes
mais un avertissement est emis au demarrage (cf. core.security.api_key).

Contrat preserve : /api/v1/webhook/n8n reste fail-closed au niveau ROUTEUR
(403), PAS 401 au niveau middleware — il n'est pas dans _PROTECTED_PREFIXES.
"""

import importlib
import sys
import warnings

import pytest
from fastapi.testclient import TestClient

ROOT = r"G:\AI\E-zzio"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

KEY = "une-cle-solide-aleatoire-0123456789"


def _reload_server(monkeypatch, key: str | None, disable_auth: str = "0"):
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


# (methode, chemin) — surfaces qui DOIVENT exiger la cle quand elle est posee.
AUTHENTICATED_SURFACES = [
    ("GET", "/api/files"),
    ("GET", "/api/files/content?path=README.md"),
    ("GET", "/api/memory"),
    ("GET", "/api/memory/content?path=package.json"),
    ("GET", "/api/automations"),
    ("GET", "/api/missions"),
    ("GET", "/api/projects"),
    ("GET", "/api/objectives"),
    ("GET", "/api/approvals"),
    ("GET", "/api/settings/thinking"),
    ("POST", "/api/kill"),
]

PRIVILEGED_SURFACES = [
    ("POST", "/api/models/select"),
    ("GET", "/api/accounts/providers"),
]


def _call(client, method: str, path: str, headers=None):
    if method == "POST":
        return client.post(path, json={}, headers=headers)
    return client.get(path, headers=headers)


class TestSensitiveSurfacesRequireKeyWhenConfigured:
    @pytest.mark.parametrize("method,path", AUTHENTICATED_SURFACES + PRIVILEGED_SURFACES)
    def test_missing_header_is_401(self, client_factory, method, path):
        c = client_factory(key=KEY)
        assert _call(c, method, path).status_code == 401

    @pytest.mark.parametrize("method,path", AUTHENTICATED_SURFACES + PRIVILEGED_SURFACES)
    def test_wrong_header_is_401(self, client_factory, method, path):
        c = client_factory(key=KEY, )
        assert _call(c, method, path, headers={"X-API-Key": "mauvaise"}).status_code == 401

    @pytest.mark.parametrize("method,path", AUTHENTICATED_SURFACES + PRIVILEGED_SURFACES)
    def test_correct_header_is_not_401(self, client_factory, method, path):
        c = client_factory(key=KEY)
        r = _call(c, method, path, headers={"X-API-Key": KEY})
        assert r.status_code != 401


class TestPublicSurfacesStayPublic:
    def test_health_is_never_401_with_key(self, client_factory):
        c = client_factory(key=KEY)
        assert c.get("/health").status_code != 401

    def test_health_is_never_401_without_key(self, client_factory):
        c = client_factory(key=None)
        assert c.get("/health").status_code != 401


class TestDevModePreserved:
    """Aucune cle configuree => comportement de dev preserve (pas de 401)."""

    @pytest.mark.parametrize("method,path", AUTHENTICATED_SURFACES[:5])
    def test_open_when_no_key(self, client_factory, method, path):
        c = client_factory(key=None)
        assert _call(c, method, path).status_code != 401

    def test_disable_auth_flag_bypasses_sensitive_surfaces(self, client_factory):
        c = client_factory(key=KEY, disable_auth="1")
        assert c.get("/api/files").status_code != 401


class TestWebhookClassificationUnchanged:
    """Le webhook reste fail-closed au ROUTEUR (403), pas 401 middleware."""

    def test_webhook_not_captured_by_prefix_rule(self, client_factory):
        c = client_factory(key=KEY)
        r = c.post(
            "/api/v1/webhook/n8n",
            json={"intent": "x", "response": "y"},
            headers={"X-API-Key": "mauvaise"},
        )
        assert r.status_code == 403


class TestRouterLevelDefenseInDepth:
    """Les routeurs /api sensibles ne doivent pas non plus exposer de cle en dur."""

    def test_no_hardcoded_key_in_api_endpoints(self):
        import core.api.endpoints as endpoints

        assert not hasattr(endpoints, "EXPECTED_KEY")
