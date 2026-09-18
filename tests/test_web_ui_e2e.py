"""E-ZZIO Web UI E2E tests.

DETTE TECHNIQUE IDENTIFIEE (2026-09-19) :
    Brave 153+ sur Windows crashe immediatement (rc=0xC0000005)
    quand lance avec --remote-debugging-port, meme en headless.
    Cela affecte tous les tests qui necessitent un browser CDP.

    Cause probable : conflit avec une instance Brave perso deja active,
    ou bug Brave 153 sur Windows.

    Ces tests sont desactives jusqu'a resolution.

    Solutions a explorer (session dediee) :
      1. Utiliser Chrome (pas Brave) pour les tests E2E
      2. Utiliser Playwright (gestion browser integree)
      3. Investiguer le bug Brave 153 headless
"""

import pytest


pytestmark = pytest.mark.skip(
    reason=(
        "Brave 153+ sur Windows crashe en CDP (rc=0xC0000005). "
        "Dette technique documentee dans docs/E2E_TECHNICAL_DEBT.md. "
        "Voir session dediee pour reparation (Chrome/Playwright)."
    )
)


def test_e2e_disabled_notice():
    """Test placeholder : indique que les E2E sont desactives."""
    pass