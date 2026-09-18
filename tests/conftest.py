# ════════════════════════════════════════════════════════════════════════════
# tests/conftest.py — Fixtures partagées
# ════════════════════════════════════════════════════════════════════════════

import pytest


@pytest.fixture(scope="session")
def chrome_cdp():
    """Fixture session : lance Brave/Chrome isolé en CDP.

    Retourne le port CDP (int).

    ⚠️  SÉCURITÉ : ne touche JAMAIS aux autres process Brave/Chrome
    de l'utilisateur. Port dynamique + profil isolé + PID tracké.
    """
    try:
        from tests._browser_helper import isolated_brave_cdp
    except ImportError:
        from _browser_helper import isolated_brave_cdp

    with isolated_brave_cdp(headless=True) as (proc, port):
        yield port