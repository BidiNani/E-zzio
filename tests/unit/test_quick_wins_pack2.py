"""Tests Paquet 2 quick wins : 5 fichiers a 100%.

- core/utils/http_pool.py : get_http_client + close_http_client
- core/config/iconfig_provider.py : IConfigProvider ABC
- core/providers/google_calendar_provider.py : stub + except
- core/providers/google_docs_provider.py : stub + except
- core/providers/google_drive_provider.py : stub + except
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================
# 1. core/utils/http_pool.py
# ============================================================

class TestHttpPool:
    def test_get_http_client_creates_singleton(self):
        """Premier appel -> cree un AsyncClient."""
        from core.utils import http_pool
        # Reset global pour etre propre
        http_pool._global_async_client = None

        client = http_pool.get_http_client()
        try:
            assert client is not None
            # Deuxieme appel -> meme instance
            client2 = http_pool.get_http_client()
            assert client2 is client
        finally:
            # Cleanup
            http_pool._global_async_client = None

    def test_get_http_client_custom_timeout(self):
        from core.utils import http_pool
        http_pool._global_async_client = None

        client = http_pool.get_http_client(timeout=5.0)
        try:
            assert client is not None
        finally:
            http_pool._global_async_client = None

    @pytest.mark.asyncio
    async def test_close_http_client_none(self):
        """close_http_client avec client=None -> ne fait rien."""
        from core.utils import http_pool
        http_pool._global_async_client = None
        # Ne doit pas lever
        await http_pool.close_http_client()
        assert http_pool._global_async_client is None

    @pytest.mark.asyncio
    async def test_close_http_client_already_closed(self):
        """close_http_client avec client deja ferme -> ne fait rien."""
        from core.utils import http_pool
        mock_client = MagicMock()
        mock_client.is_closed = True
        http_pool._global_async_client = mock_client
        try:
            await http_pool.close_http_client()
            # Ne doit pas appeler aclose()
            mock_client.aclose.assert_not_called()
        finally:
            http_pool._global_async_client = None

    @pytest.mark.asyncio
    async def test_close_http_client_open(self):
        """close_http_client avec client ouvert -> aclose + reset None."""
        from core.utils import http_pool
        mock_client = MagicMock()
        mock_client.is_closed = False
        mock_client.aclose = AsyncMock()
        http_pool._global_async_client = mock_client
        try:
            await http_pool.close_http_client()
            # aclose doit avoir ete appele
            mock_client.aclose.assert_awaited_once()
            # Le global doit etre None
            assert http_pool._global_async_client is None
        finally:
            http_pool._global_async_client = None


# ============================================================
# 2. core/config/iconfig_provider.py
# ============================================================

class TestIConfigProvider:
    def test_icannot_instantiate_abstract(self):
        """IConfigProvider ne peut pas etre instancie directement."""
        from core.config.iconfig_provider import IConfigProvider
        with pytest.raises(TypeError):
            IConfigProvider()

    def test_concrete_subclass_works(self):
        """Une sous-classe concrete implementant les 3 methodes est instanciable."""
        from core.config.iconfig_provider import IConfigProvider

        class ConcreteConfig(IConfigProvider):
            async def get_config(self, key):
                return {"key": key}

            async def set_config(self, key, value):
                pass

            async def list_configs(self, prefix=""):
                return {"prefix": prefix}

        obj = ConcreteConfig()
        assert isinstance(obj, IConfigProvider)

    @pytest.mark.asyncio
    async def test_concrete_methods(self):
        from core.config.iconfig_provider import IConfigProvider

        class ConcreteConfig(IConfigProvider):
            async def get_config(self, key):
                return {"key": key}

            async def set_config(self, key, value):
                self.last_set = (key, value)

            async def list_configs(self, prefix=""):
                return {"prefix": prefix}

        obj = ConcreteConfig()
        assert await obj.get_config("a") == {"key": "a"}
        await obj.set_config("b", 42)
        assert obj.last_set == ("b", 42)
        assert await obj.list_configs("x") == {"prefix": "x"}

    def test_incomplete_subclass_raises(self):
        """Sous-classe incomplete -> TypeError."""
        from core.config.iconfig_provider import IConfigProvider

        class Incomplete(IConfigProvider):
            async def get_config(self, key):
                return None
            # set_config et list_configs manquent

        with pytest.raises(TypeError):
            Incomplete()


# ============================================================
# 3-5. Google Providers
# ============================================================

@pytest.mark.parametrize(
    ("module_path", "class_name", "provider_key"),
    [
        ("core.providers.google_calendar_provider", "GoogleCalendarProvider", "google_calendar"),
        ("core.providers.google_docs_provider", "GoogleDocsProvider", "google_docs"),
        ("core.providers.google_drive_provider", "GoogleDriveProvider", "google_drive"),
    ],
)
class TestGoogleProviders:
    def test_provider_instantiable_with_explicit_key(self, module_path, class_name, provider_key):
        """Avec api_key explicite -> pas d'erreur."""
        import importlib
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        with patch.object(mod, "load_secrets", return_value=True):
            provider = cls(api_key="explicit_key_12345")
        assert provider.api_key == "explicit_key_12345"

    def test_provider_vault_exception_path(self, module_path, class_name, provider_key):
        """Si l'import vault leve -> _vault_key=None, fallback sur env."""
        import importlib
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)

        # Simuler un echec de l'import vault en injectant un module casse
        def import_raiser(*args, **kwargs):
            raise ImportError("simulated vault failure")

        with patch.object(mod, "load_secrets", return_value=True):
            with patch.dict("sys.modules", {"core.security.unified_vault": None}):
                # Force le except via import error
                with patch("builtins.__import__", side_effect=import_raiser):
                    provider = cls(api_key="fallback")
        # api_key explicite -> pas besoin du vault
        assert provider.api_key == "fallback"

    @pytest.mark.asyncio
    async def test_provider_execute_not_implemented(self, module_path, class_name, provider_key):
        """execute() leve NotImplementedError."""
        import importlib
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        with patch.object(mod, "load_secrets", return_value=True):
            provider = cls(api_key="test_key")
        with pytest.raises(NotImplementedError):
            await provider.execute()

    def test_provider_inherits_igoogle(self, module_path, class_name, provider_key):
        """Verifier l'heritage de IGoogleProvider."""
        import importlib

        from core.providers.igoogle_provider import IGoogleProvider
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        assert issubclass(cls, IGoogleProvider)
