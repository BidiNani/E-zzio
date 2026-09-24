"""Tests Phase 2.2 — ProviderRegistry + ProviderFactory."""
from __future__ import annotations

import pytest

# ============================================================
# 1. ProviderRegistry
# ============================================================

class TestProviderRegistry:
    def test_list_providers_returns_5(self):
        from core.providers.registry import ProviderRegistry

        providers = ProviderRegistry.list_providers()
        assert "gemini" in providers
        assert "groq" in providers
        assert "openrouter" in providers
        assert "nvidia" in providers
        assert "ollama" in providers
        assert len(providers) == 5

    def test_list_providers_is_sorted(self):
        from core.providers.registry import ProviderRegistry

        providers = ProviderRegistry.list_providers()
        assert providers == sorted(providers)

    def test_has_known_provider(self):
        from core.providers.registry import ProviderRegistry

        assert ProviderRegistry.has("gemini") is True
        assert ProviderRegistry.has("groq") is True
        assert ProviderRegistry.has("ollama") is True

    def test_has_unknown_provider(self):
        from core.providers.registry import ProviderRegistry

        assert ProviderRegistry.has("unknown_provider") is False
        assert ProviderRegistry.has("") is False

    def test_get_class_unknown_raises(self):
        from core.providers.registry import (
            ProviderNotFoundError,
            ProviderRegistry,
        )

        with pytest.raises(ProviderNotFoundError, match="inconnu"):
            ProviderRegistry.get_class("nonexistent")

    def test_get_class_known_returns_class(self):
        from core.providers.base_provider import BaseProvider
        from core.providers.registry import ProviderRegistry

        cls = ProviderRegistry.get_class("gemini")
        assert issubclass(cls, BaseProvider)
        assert cls.__name__ == "GeminiProvider"

    def test_get_class_import_error(self):
        """Si un provider enregistré n'existe pas, ImportError."""
        from core.providers.registry import ProviderRegistry

        # Patcher temporairement le registre
        original = ProviderRegistry._REGISTRY.copy()
        try:
            ProviderRegistry._REGISTRY["fake"] = "core.providers.nonexistent:FakeProvider"
            with pytest.raises(ImportError):
                ProviderRegistry.get_class("fake")
        finally:
            ProviderRegistry._REGISTRY = original


# ============================================================
# 2. ProviderFactory
# ============================================================

class TestProviderFactory:
    def test_create_unknown_raises(self):
        from core.providers.registry import (
            ProviderFactory,
            ProviderNotFoundError,
        )

        with pytest.raises(ProviderNotFoundError, match="inconnu"):
            ProviderFactory.create("nonexistent")

    def test_create_gemini(self):
        from core.providers.base_provider import BaseProvider
        from core.providers.registry import ProviderFactory

        provider = ProviderFactory.create("gemini")
        assert isinstance(provider, BaseProvider)

    def test_create_groq(self):
        from core.providers.base_provider import BaseProvider
        from core.providers.registry import ProviderFactory

        provider = ProviderFactory.create("groq")
        assert isinstance(provider, BaseProvider)

    def test_create_openrouter(self):
        from core.providers.base_provider import BaseProvider
        from core.providers.registry import ProviderFactory

        provider = ProviderFactory.create("openrouter")
        assert isinstance(provider, BaseProvider)

    def test_create_nvidia(self):
        from core.providers.base_provider import BaseProvider
        from core.providers.registry import ProviderFactory

        provider = ProviderFactory.create("nvidia")
        assert isinstance(provider, BaseProvider)

    def test_create_ollama(self):
        from core.providers.base_provider import BaseProvider
        from core.providers.registry import ProviderFactory

        provider = ProviderFactory.create("ollama")
        assert isinstance(provider, BaseProvider)

    def test_create_with_kwargs(self):
        """Test qu'on peut passer des kwargs au constructeur."""
        from core.providers.registry import ProviderFactory

        # On ne sait pas quels kwargs sont acceptes, mais l'appel ne doit pas
        # lever de TypeError pour un provider connu
        provider = ProviderFactory.create("gemini")
        assert provider is not None

    def test_create_returns_new_instance(self):
        """Chaque appel retourne une nouvelle instance."""
        from core.providers.registry import ProviderFactory

        p1 = ProviderFactory.create("gemini")
        p2 = ProviderFactory.create("gemini")
        assert p1 is not p2


# ============================================================
# 3. Integration — list + create
# ============================================================

class TestRegistryFactoryIntegration:
    def test_all_registered_providers_can_be_created(self):
        """Tous les providers enregistrés peuvent être créés."""
        from core.providers.registry import ProviderFactory, ProviderRegistry

        for name in ProviderRegistry.list_providers():
            provider = ProviderFactory.create(name)
            assert provider is not None

    def test_registry_matches_factory(self):
        """Chaque provider du registre est créable par la factory."""
        from core.providers.registry import ProviderFactory, ProviderRegistry

        for name in ProviderRegistry.list_providers():
            assert ProviderRegistry.has(name)
            provider = ProviderFactory.create(name)
            assert provider is not None
