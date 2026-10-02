# tests/conftest.py - Fixtures partagees
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# ============================================================
# ISOLATION GLOBALE DU LEDGER BUDGETAIRE
# ============================================================
# CognitiveGovernor lit et ecrit un ledger persistant et signe en HMAC :
#   runtime/cognition/budget/cognitive_budget_ledger.jsonl
# Ce ledger est un etat MUT sur disque, avec un plafond de session de
# 500 000 tokens. Une fois sature, evaluate_and_record() refuse TOUTE
# nouvelle mission ("Budget insuffisant. Restant: 0 tokens"), ce qui
# faisait echouer une vingtaine de suites de tests selon leur ordre
# d'execution : un test heritant du budget consomme par un test
# precedent, etait en realite non deterministe.
#
# On rend donc la session de tests hermetique : tout gouverneur cree
# SANS argument explicite est redirige vers un dossier temporaire propre,
# avec un ledger vierge et un budget au plafond nominal.
#
# Pourquoi ne pas rediriger EZZIO_ROOT ?
#   La racine de projet est aussi le workspace_root d'EzzioMaster : la
#   rediriger ferait ecrire les Gates A/B dans un dossier vide au lieu
#   du depot, et ferait echouer les tests qui lisent les sources du
#   projet. On n'ecole donc que le gouverneur, dont la seule fonction est
#   le ledger.
#
# Aucun fichier de production n'est modifie : le patch est applique en
# memoire sur la classe, et il est retire en fin de session. Les
# signatures HMAC du ledger reel restent intactes.

_TEST_BUDGET_ENV = "EZZIO_TEST_BUDGET_ROOT"
_ORIGINAL_GOVERNOR_INIT = None


def _patch_governor_root(budget_root):
    """Redirige tout CognitiveGovernor cree sans argument vers budget_root.

    Doit etre appele AVANT l'import des modules de test : core.ezzio_master
    instancie un singleton `ezzio_master = EzzioMaster()` au niveau module,
    donc son governor est cree au moment de l'import, bien avant toute
    fixture. Un patch applique en fixture laissait donc ce governor la
    production.
    """
    global _ORIGINAL_GOVERNOR_INIT
    from core.cognition import cognitive_governor as gov_mod

    if _ORIGINAL_GOVERNOR_INIT is None:
        _ORIGINAL_GOVERNOR_INIT = gov_mod.CognitiveGovernor.__init__

    original_init = _ORIGINAL_GOVERNOR_INIT

    def _patched_init(self, root_dir=None):
        # root_dir explicite : l'appelant choisit son isolation, on respecte
        # son choix (ex: un tmp_path fourni par le test lui-meme).
        if root_dir is None:
            root_dir = budget_root
        original_init(self, root_dir)

    gov_mod.CognitiveGovernor.__init__ = _patched_init
    os.environ[_TEST_BUDGET_ENV] = str(budget_root)


def pytest_configure(config):
    """Isole le ledger budgetaire avant toute collecte de test.

    Le dossier temporaire est cree ici (et non via tmp_path_factory) car le
    patch doit etre actif avant l'import des modules de test, donc avant
    toute fixture.
    """
    import atexit
    import tempfile

    budget_root = Path(tempfile.mkdtemp(prefix="ezzio_test_budget_"))
    _patch_governor_root(budget_root)
    config._ezzio_test_budget_root = budget_root

    def _cleanup():
        global _ORIGINAL_GOVERNOR_INIT
        if _ORIGINAL_GOVERNOR_INIT is not None:
            try:
                from core.cognition import cognitive_governor as gov_mod

                gov_mod.CognitiveGovernor.__init__ = _ORIGINAL_GOVERNOR_INIT
            except Exception:
                pass
        os.environ.pop(_TEST_BUDGET_ENV, None)

    atexit.register(_cleanup)


@pytest.fixture(scope="session")
def isolated_budget_root(request):
    """Expose le dossier budgetaire isole, pour les tests qui le reclament."""
    return Path(request.config._ezzio_test_budget_root)


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

# FIX-FLAKY : nettoyage d'etat entre tests pour eviter les fuites
# (event loop, patches, sys.modules). Certains tests laissent un etat
# qui casse les tests suivants quand on lance tests/unit/ en entier.
import asyncio
import gc
import sys

import pytest


@pytest.fixture(autouse=True)
def _clean_state_between_tests():
    """Nettoie l'etat partage entre chaque test (evite flaky)."""
    yield
    # 1. Fermer les event loops orphelines
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            loop = asyncio.get_event_loop_policy().get_event_loop()
            if loop and not loop.is_closed() and not loop.is_running():
                loop.close()
    except Exception:
        pass

    # 2. Forcer un GC pour nettoyer les references
    gc.collect()

# ============================================================
# STABILISATION ENV — cv2/numpy (import unique)
# ============================================================
import sys as _sys


def _stabilize_native_modules():
    """Force l'import unique de cv2/numpy au debut de la session pytest.

    Sans cela, un test qui recharge numpy (via importlib.reload)
    provoque 'cannot load module more than once per process' pour cv2.
    """
    if "cv2" in _sys.modules and "numpy" in _sys.modules:
        return
    try:
        import cv2  # noqa: F401
        import numpy  # noqa: F401
    except ImportError:
        # OpenCV/numpy absents : les tests concernes seront skip
        pass


# Import au chargement de conftest = avant tous les tests
_stabilize_native_modules()
