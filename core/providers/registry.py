"""
E-ZZIO Core — Provider Registry (Phase 2.2).

Registre canonique des providers disponibles. Fournit une **autorité unique**
pour la résolution des providers, remplaçant les branches `if provider == ...`
disséminées dans le code.

Principes :
- Fail-closed : si un provider est inconnu, on lève une erreur explicite.
- Lazy loading : les providers sont importés au moment de la création.
- Extensible : enregistrer un nouveau provider = 1 ligne dans `_REGISTRY`.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from core.providers.base_provider import BaseProvider

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ProviderNotFoundError(RuntimeError):
    """Provider inconnu dans le registre."""


class ProviderRegistry:
    """
    Registre canonique des providers.

    Usage :
        ProviderRegistry.list_providers() -> ["gemini", "groq", ...]
        ProviderRegistry.has("gemini") -> True
        provider = ProviderFactory.create("gemini")
    """

    # Mapping name -> "module:Class" (lazy import)
    _REGISTRY: dict[str, str] = {
        "gemini": "core.providers.gemini_provider:GeminiProvider",
        "groq": "core.providers.groq_provider:GroqProvider",
        "openrouter": "core.providers.openrouter_provider:OpenRouterProvider",
        "nvidia": "core.providers.nvidia_nim_provider:NvidiaNimProvider",
        "ollama": "core.providers.ollama_provider:OllamaProvider",
    }

    @classmethod
    def list_providers(cls) -> list[str]:
        """Retourne la liste triée des providers enregistrés."""
        return sorted(cls._REGISTRY.keys())

    @classmethod
    def has(cls, name: str) -> bool:
        """Vérifie si un provider est enregistré."""
        return name in cls._REGISTRY

    @classmethod
    def get_class(cls, name: str) -> type[BaseProvider]:
        """
        Retourne la classe du provider (lazy import).

        Raise:
            ProviderNotFoundError : si le provider n'est pas enregistré.
            ImportError : si le module du provider ne peut pas être importé.
        """
        if name not in cls._REGISTRY:
            available = ", ".join(cls.list_providers())
            raise ProviderNotFoundError(
                f"Provider inconnu : {name!r}. Disponibles : {available}"
            )

        target = cls._REGISTRY[name]
        module_path, class_name = target.split(":")
        try:
            import importlib
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except (ImportError, AttributeError) as exc:
            raise ImportError(
                f"Impossible de charger le provider {name!r} ({target}) : {exc}"
            ) from exc


class ProviderFactory:
    """
    Factory canonique des providers.

    Usage :
        provider = ProviderFactory.create("gemini", model="gemini-3.5-flash")
        # provider est une instance de GeminiProvider

        # Avec kwargs par défaut
        provider = ProviderFactory.create("ollama")
    """

    @staticmethod
    def create(name: str, **kwargs: Any) -> BaseProvider:
        """
        Crée une instance de provider.

        Args:
            name : nom canonique du provider (gemini, groq, openrouter, nvidia, ollama)
            **kwargs : passés au constructeur du provider

        Returns:
            Instance de BaseProvider.

        Raise:
            ProviderNotFoundError : si le provider n'est pas enregistré.
        """
        provider_class = ProviderRegistry.get_class(name)
        logger.debug("[ProviderFactory] Création provider %r (%s)", name, provider_class.__name__)
        return provider_class(**kwargs)


# ============================================================
# Auto-enregistrement au chargement
# ============================================================

def _list_available() -> list[str]:
    """Utilitaire : liste les providers disponibles."""
    return ProviderRegistry.list_providers()


__all__ = [
    "ProviderNotFoundError",
    "ProviderRegistry",
    "ProviderFactory",
]
