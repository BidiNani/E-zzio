"""Tests Paquet 1 quick wins : 5 fichiers a 100%.

- core/cognition/__init__.py : Init class
- core/talents/analyser.py : Analyser.run (async)
- core/models/ezzio_router.py : EzzioRouter.invalidate_cache
- core/secrets.py : get_secrets_path, load_secrets, get_api_key
- core/security/quota_manager.py : QuotaManager (async sqlite)
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================
# 1. core/cognition/__init__.py
# ============================================================

class TestCognitionInit:
    def test_init_instantiable(self):
        from core.cognition import Init
        obj = Init()
        assert isinstance(obj, Init)

    def test_init_class_name(self):
        from core.cognition import Init
        obj = Init()
        assert obj.__class__.__name__ == "Init"


# ============================================================
# 2. core/talents/analyser.py
# ============================================================

class TestAnalyser:
    def test_analyser_inherits_base_talent(self):
        from core.talents.analyser import Analyser
        from core.talents.base_talent import BaseTalent
        assert issubclass(Analyser, BaseTalent)

    def test_analyser_default_name(self):
        from core.talents.analyser import Analyser
        a = Analyser()
        assert a.name == "analyser"

    @pytest.mark.asyncio
    async def test_analyser_run_calls_query_model(self):
        from core.talents import analyser as an_mod
        mock_query = AsyncMock(return_value="Analyse factuelle")
        with patch.object(an_mod, "query_model_async", mock_query):
            a = an_mod.Analyser()
            result = await a.run("Contenu a analyser")
        assert result == "Analyse factuelle"
        mock_query.assert_awaited_once()
        call = mock_query.await_args
        assert call.kwargs["organ_key"] == "analysis"
        assert call.kwargs["speed"] == "normal"
        prompt_arg = call.args[0]
        assert "Contenu a analyser" in prompt_arg


# ============================================================
# 3. core/models/ezzio_router.py
# ============================================================

class TestEzzioRouter:
    def test_router_init_stores_attrs(self):
        from core.models.ezzio_router import EzzioRouter
        with patch("core.models.ezzio_router.LiteLLM_BaseRouter.__init__", return_value=None):
            r = EzzioRouter(registry="reg", key_pool="kp", telemetry="tel")
        assert r.registry == "reg"
        assert r.key_pool == "kp"
        assert r.telemetry == "tel"

    def test_router_init_defaults_none(self):
        from core.models.ezzio_router import EzzioRouter
        with patch("core.models.ezzio_router.LiteLLM_BaseRouter.__init__", return_value=None):
            r = EzzioRouter()
        assert r.registry is None
        assert r.key_pool is None
        assert r.telemetry is None

    def test_invalidate_cache_calls_super_when_present(self):
        from core.models.ezzio_router import EzzioRouter
        with patch("core.models.ezzio_router.LiteLLM_BaseRouter.__init__", return_value=None):
            r = EzzioRouter()
        with patch.object(
            type(r).__mro__[1],
            "invalidate_cache",
            MagicMock(),
            create=True,
        ) as mock_inv:
            r.invalidate_cache("a", "b")
            mock_inv.assert_called_once_with("a", "b")

    def test_invalidate_cache_no_super_method(self):
        from core.models.ezzio_router import EzzioRouter
        with patch("core.models.ezzio_router.LiteLLM_BaseRouter.__init__", return_value=None):
            r = EzzioRouter()
        with patch("builtins.hasattr", return_value=False):
            r.invalidate_cache()


# ============================================================
# 4. core/secrets.py
# ============================================================

class TestSecrets:
    def test_get_secrets_path(self):
        from core.secrets import get_secrets_path
        path = get_secrets_path()
        assert isinstance(path, Path)
        assert path.name == ".env"
        assert path.parent.name == "secrets"

    def test_load_secrets_returns_bool_true(self):
        """load_secrets retourne True quand loader.load retourne truthy."""
        import core.config.secrets_loader as loader_mod
        from core import secrets as sec_mod
        with patch.object(loader_mod, "load", return_value=True) as mock_load:
            result = sec_mod.load_secrets()
        assert result is True
        mock_load.assert_called_once_with(override=True)

    def test_load_secrets_returns_bool_false(self):
        """load_secrets retourne False quand loader.load retourne falsy."""
        import core.config.secrets_loader as loader_mod
        from core import secrets as sec_mod
        with patch.object(loader_mod, "load", return_value=False) as mock_load:
            result = sec_mod.load_secrets()
        assert result is False
        mock_load.assert_called_once_with(override=True)

    def test_load_secrets_override_false(self):
        """override=False passe bien a loader.load."""
        import core.config.secrets_loader as loader_mod
        from core import secrets as sec_mod
        with patch.object(loader_mod, "load", return_value=True) as mock_load:
            sec_mod.load_secrets(override=False)
        mock_load.assert_called_once_with(override=False)

    def test_get_api_key_reads_env(self):
        from core import secrets as sec_mod
        with patch.dict(os.environ, {"MY_TEST_KEY": "secret_value"}):
            with patch.object(sec_mod, "load_secrets", return_value=True):
                result = sec_mod.get_api_key("MY_TEST_KEY")
        assert result == "secret_value"

    def test_get_api_key_missing_returns_empty(self):
        from core import secrets as sec_mod
        with patch.object(sec_mod, "load_secrets", return_value=True):
            result = sec_mod.get_api_key("THIS_KEY_DOES_NOT_EXIST_12345")
        assert result == ""


# ============================================================
# 5. core/security/quota_manager.py
# ============================================================

def _make_mock_db(fetchone_value=(0,)):
    """Construit un mock async de connexion aiosqlite."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone = AsyncMock(return_value=fetchone_value)
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_cursor)
    mock_db.commit = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)
    return mock_db


class TestQuotaManager:
    def test_quota_exceeded_error(self):
        from core.security.quota_manager import QuotaExceededError
        err = QuotaExceededError("test")
        assert isinstance(err, Exception)
        assert "test" in str(err)

    def test_manager_init_attrs(self):
        from core.security.quota_manager import QuotaManager
        qm = QuotaManager(db_path="test.db")
        assert qm.db_path == "test.db"
        assert qm.HOURLY_LIMITS["gemini"] == 10
        assert qm.HOURLY_LIMITS["tavily"] == 50

    @pytest.mark.asyncio
    async def test_init_creates_table(self):
        """Couvre L21-30 : init() execute CREATE TABLE + commit."""
        from core.security import quota_manager as qm_mod
        qm = qm_mod.QuotaManager(db_path=":memory:")

        mock_db = _make_mock_db()

        with patch.object(qm_mod.aiosqlite, "connect", return_value=mock_db):
            await qm.init()

        # Verifier que execute a ete appele (CREATE TABLE)
        assert mock_db.execute.await_count >= 1
        # Verifier que commit a ete appele
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_and_increment_swallows_init_error(self):
        """L34-36 : si init() leve, on continue sans crasher."""
        from core.security import quota_manager as qm_mod
        qm = qm_mod.QuotaManager(db_path=":memory:")
        qm.init = AsyncMock(side_effect=RuntimeError("init failed"))

        mock_db = _make_mock_db(fetchone_value=(0,))

        with patch.object(qm_mod.aiosqlite, "connect", return_value=mock_db):
            result = await qm.check_and_increment("user1", "gemini")

        assert result is True
        qm.init.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_and_increment_raises_when_quota_reached(self):
        """Quota atteint -> QuotaExceededError."""
        from core.security import quota_manager as qm_mod
        qm = qm_mod.QuotaManager(db_path=":memory:")
        qm.init = AsyncMock()

        mock_db = _make_mock_db(fetchone_value=(10,))

        with patch.object(qm_mod.aiosqlite, "connect", return_value=mock_db):
            with pytest.raises(qm_mod.QuotaExceededError):
                await qm.check_and_increment("user1", "gemini")

    @pytest.mark.asyncio
    async def test_check_and_increment_unknown_provider_defaults_10(self):
        """Provider inconnu -> limite par defaut = 10."""
        from core.security import quota_manager as qm_mod
        qm = qm_mod.QuotaManager(db_path=":memory:")
        qm.init = AsyncMock()

        mock_db = _make_mock_db(fetchone_value=(5,))

        with patch.object(qm_mod.aiosqlite, "connect", return_value=mock_db):
            result = await qm.check_and_increment("user1", "unknown_provider")

        assert result is True
