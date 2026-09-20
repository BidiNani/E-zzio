import pytest

pytestmark = pytest.mark.integration

"""
Test unitaire direct du rate limiter, sans HTTP ni appel LLM.
Objectif : verifier check_rate_limit() en quelques millisecondes,
au lieu de dependre de la latence d'Ollama (30-50s/appel) qui rend
tout test via HTTP end-to-end lent et ambigu.
"""

import time

import pytest


@pytest.fixture
def rate_limit_module(monkeypatch, tmp_path):
    """Charge routers.webhook avec une base SQLite temporaire isolée."""
    import routers.webhook as webhook

    # Isolation de la DB pour les tests
    test_db = tmp_path / "rate_limit_test.db"
    monkeypatch.setattr(webhook, "RATE_LIMIT_DB", test_db)

    # On force la réinitialisation de la DB temporaire
    webhook.init_rate_limit_db()

    return webhook


def test_allows_up_to_max_requests(rate_limit_module):
    """Les 10 premières requêtes d'une même IP doivent passer."""
    for _ in range(10):
        assert rate_limit_module.check_rate_limit("1.2.3.4", max_requests=10, window_sec=60.0) is True


def test_blocks_after_max_requests(rate_limit_module):
    """La 11e requête dans la même fenêtre doit être rejetée."""
    for _ in range(10):
        rate_limit_module.check_rate_limit("1.2.3.4", max_requests=10, window_sec=60.0)
    assert rate_limit_module.check_rate_limit("1.2.3.4", max_requests=10, window_sec=60.0) is False


def test_different_ips_have_separate_limits(rate_limit_module):
    """Une IP différente ne doit pas être affectée par le quota d'une autre."""
    for _ in range(10):
        rate_limit_module.check_rate_limit("1.2.3.4", max_requests=10, window_sec=60.0)

    # IP différente -> ça passe
    assert rate_limit_module.check_rate_limit("5.6.7.8", max_requests=10, window_sec=60.0) is True


def test_window_expiry_releases_quota(rate_limit_module, monkeypatch):
    """Passé la fenêtre glissante, le quota doit se libérer."""
    # Simulation du temps
    fake_now = [time.time()]
    monkeypatch.setattr(time, "time", lambda: fake_now[0])

    for _ in range(10):
        rate_limit_module.check_rate_limit("9.9.9.9", max_requests=10, window_sec=60.0)

    # Immédiatement après, c'est bloqué
    assert rate_limit_module.check_rate_limit("9.9.9.9", max_requests=10, window_sec=60.0) is False

    # On avance le temps au-delà de la fenêtre glissante (+61 secondes)
    fake_now[0] += 61.0

    # Le quota doit être réinitialisé
    assert rate_limit_module.check_rate_limit("9.9.9.9", max_requests=10, window_sec=60.0) is True
