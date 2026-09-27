"""
Tests de securite pour la resolution de la cle d'API.

Contexte : `routers/stats.py`, `routers/system.py` et `routers/webhook.py`
utilisaient `os.getenv("EZZIO_API_KEY", "ezzio_secret_key_local_dev")`.
Cette cle etant publique dans le code source, `/api/v1/webhook/n8n` — monte
dans web_server.py — etait accessible a quiconque avait lu le depot.
"""

import pytest

from core.security.api_key import (
    ENV_KEY,
    LEGACY_INSECURE_DEFAULTS,
    is_key_configured,
    is_key_valid,
    is_using_insecure_default,
    resolve_expected_key,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv(ENV_KEY, raising=False)


class TestFailClosed:
    """Aucune cle configuree => personne ne passe."""

    def test_no_key_rejects_any_provided_key(self):
        assert resolve_expected_key() == ""
        assert is_key_configured() is False
        assert is_key_valid("nimporte-quoi") is False

    def test_no_key_rejects_none_and_empty(self):
        assert is_key_valid(None) is False
        assert is_key_valid("") is False

    def test_whitespace_only_key_is_treated_as_absent(self, monkeypatch):
        monkeypatch.setenv(ENV_KEY, "   ")
        assert resolve_expected_key() == ""
        assert is_key_valid("   ") is False


class TestValidKey:
    def test_matching_key_accepted(self, monkeypatch):
        monkeypatch.setenv(ENV_KEY, "vraie-cle-1234")
        assert is_key_configured() is True
        assert is_key_valid("vraie-cle-1234") is True

    def test_wrong_key_rejected(self, monkeypatch):
        monkeypatch.setenv(ENV_KEY, "vraie-cle-1234")
        assert is_key_valid("mauvaise") is False

    def test_prefix_of_key_rejected(self, monkeypatch):
        monkeypatch.setenv(ENV_KEY, "vraie-cle-1234")
        assert is_key_valid("vraie") is False

    def test_key_is_trimmed(self, monkeypatch):
        monkeypatch.setenv(ENV_KEY, "  vraie-cle-1234  ")
        assert resolve_expected_key() == "vraie-cle-1234"
        assert is_key_valid("vraie-cle-1234") is True


class TestPublicDefaultsRejected:
    """Les valeurs par defaut historiquement publiees ne doivent jamais passer."""

    @pytest.mark.parametrize("legacy", sorted(LEGACY_INSECURE_DEFAULTS))
    def test_legacy_default_is_flagged_and_refused(self, monkeypatch, legacy):
        monkeypatch.setenv(ENV_KEY, legacy)
        assert is_using_insecure_default() is True
        assert is_key_valid(legacy) is False

    def test_legacy_default_not_accepted_even_with_matching_input(self, monkeypatch):
        # Piege : detecter n'est pas rejeter. Avant correction, cette cle
        # publique passait l'authentification.
        monkeypatch.setenv(ENV_KEY, "ezzio_secret_key_local_dev")
        assert is_key_valid("ezzio_secret_key_local_dev") is False

    def test_normal_key_is_not_flagged(self, monkeypatch):
        monkeypatch.setenv(ENV_KEY, "une-cle-solide-aleatoire")
        assert is_using_insecure_default() is False


class TestNoKeyMaterialInRouters:
    """Regression : plus aucune cle en dur dans les routeurs."""

    def test_routers_do_not_define_expected_key(self):
        import routers.stats
        import routers.system
        import routers.webhook

        for module in (routers.stats, routers.system, routers.webhook):
            assert not hasattr(module, "EXPECTED_KEY"), (
                f"{module.__name__} expose encore EXPECTED_KEY en dur"
            )

    def test_docker_compose_default_is_denied(self):
        # La valeur historique du docker-compose est dans la denylist.
        assert "ezzio_super_secret_session_key_2026" in LEGACY_INSECURE_DEFAULTS


class TestEnvResolution:
    def test_resolution_reads_env_each_call(self, monkeypatch):
        monkeypatch.setenv(ENV_KEY, "a")
        assert resolve_expected_key() == "a"
        monkeypatch.setenv(ENV_KEY, "b")
        assert resolve_expected_key() == "b"
        assert is_key_valid("b") is True
        assert is_key_valid("a") is False
