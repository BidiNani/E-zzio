"""E-ZZIO Core — Model Registry (auto-discovery live).

**Objectif** : interroger les APIs des providers au démarrage pour
obtenir la **liste réelle** des modèles disponibles. Aucune liste
codée en dur : les modèles obsolètes disparaissent automatiquement,
les nouveaux apparaissent automatiquement.

**Providers supportés** :
- Gemini (Google AI Studio)
- Groq
- OpenRouter (filtre uniquement les modèles gratuits)
- NVIDIA
- Ollama (local)

**Cache** : TTL de 1h pour éviter de spammer les APIs.

**Usage** :
    registry = ModelRegistry()
    models = registry.list_models("gemini")
    best = registry.pick_best_for("code", provider="groq")
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# TTL du cache (secondes)
CACHE_TTL = 3600

# Priorités des modèles par usage
# Plus le score est élevé, plus le modèle est prioritaire
MODEL_PRIORITIES = {
    # Gemini Flash (ordre décroissant)
    "gemini-3.8-flash": 100,
    "gemini-3.7-flash": 95,
    "gemini-3.6-flash": 90,
    "gemini-3.5-flash": 80,
    "gemini-3.5-flash-lite": 70,
    "gemini-2.5-flash": 60,
    "gemini-2.5-flash-lite": 50,
    # Groq
    "qwen/qwen3.8-27b": 100,
    "openai/gpt-oss-120b": 90,
    "openai/gpt-oss-20b": 80,
    # OpenRouter free
    "z-ai/glm-5.2:free": 100,
    "cohere/north-mini-code:free": 95,
    "qwen/qwen3.8-27b:free": 90,
    "nvidia/nemotron-3-ultra-550b-a55b:free": 85,
    "google/gemma-4-31b-it:free": 70,
    "google/gemma-4-26b-a4b-it:free": 65,
}


@dataclass
class ModelInfo:
    """Information d'un modèle disponible."""
    provider: str
    model_id: str
    display_name: str = ""
    context_length: int = 0
    is_free: bool = True
    raw: dict[str, Any] = field(default_factory=dict)


class ModelRegistry:
    """Registre dynamique des modèles disponibles.

    Interroge les APIs pour obtenir la liste réelle des modèles.
    Cache les résultats avec un TTL de 1h.
    """

    def __init__(self, cache_ttl: int = CACHE_TTL):
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, list[ModelInfo]]] = {}
        self._keys = self._load_keys()

    def _load_keys(self) -> dict[str, str]:
        """Charge les clés API depuis l'environnement."""
        keys = {}
        for env_var, provider in [
            ("GEMINI_API_KEY", "gemini"),
            ("GROQ_API_KEY", "groq"),
            ("OPENROUTER_API_KEY", "openrouter"),
            ("NVIDIA_API_KEY", "nvidia"),
        ]:
            val = os.environ.get(env_var)
            if val:
                keys[provider] = val
        return keys

    def _is_cache_valid(self, provider: str) -> bool:
        if provider not in self._cache:
            return False
        ts, _ = self._cache[provider]
        return (time.time() - ts) < self.cache_ttl

    def list_models(self, provider: str, force_refresh: bool = False) -> list[ModelInfo]:
        """Liste les modèles disponibles chez un provider.

        Args:
            provider: "gemini", "groq", "openrouter", "nvidia", "ollama"
            force_refresh: force un appel API même si le cache est valide

        Returns:
            Liste de ModelInfo
        """
        if not force_refresh and self._is_cache_valid(provider):
            return self._cache[provider][1]

        try:
            if provider == "gemini":
                models = self._fetch_gemini()
            elif provider == "groq":
                models = self._fetch_groq()
            elif provider == "openrouter":
                models = self._fetch_openrouter()
            elif provider == "nvidia":
                models = self._fetch_nvidia()
            elif provider == "ollama":
                models = self._fetch_ollama()
            else:
                models = []
        except Exception as exc:
            logger.warning("Échec auto-discovery %s : %s", provider, exc)
            models = []

        self._cache[provider] = (time.time(), models)
        return models

    def _fetch_gemini(self) -> list[ModelInfo]:
        """Liste les modèles Gemini disponibles."""
        key = self._keys.get("gemini")
        if not key:
            return []

        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()

        models = []
        for m in data.get("models", []):
            if "generateContent" not in m.get("supportedGenerationMethods", []):
                continue
            name = m["name"].replace("models/", "")
            models.append(ModelInfo(
                provider="gemini",
                model_id=name,
                display_name=m.get("displayName", name),
                context_length=m.get("inputTokenLimit", 0),
                is_free=True,  # Gemini free tier = accès via clé
                raw=m,
            ))
        return models

    def _fetch_groq(self) -> list[ModelInfo]:
        """Liste les modèles Groq disponibles."""
        key = self._keys.get("groq")
        if not key:
            return []

        url = "https://api.groq.com/openai/v1/models"
        headers = {"Authorization": f"Bearer {key}"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        models = []
        for m in data.get("data", []):
            models.append(ModelInfo(
                provider="groq",
                model_id=m["id"],
                display_name=m["id"],
                context_length=m.get("context_window", 0),
                is_free=True,
                raw=m,
            ))
        return models

    def _fetch_openrouter(self) -> list[ModelInfo]:
        """Liste les modèles OpenRouter GRATUITS uniquement."""
        key = self._keys.get("openrouter")
        url = "https://openrouter.ai/api/v1/models"
        headers = {"Authorization": f"Bearer {key}"} if key else {}

        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        models = []
        for m in data.get("data", []):
            pricing = m.get("pricing", {})
            prompt_price = pricing.get("prompt", "1")
            completion_price = pricing.get("completion", "1")
            if prompt_price == "0" and completion_price == "0":
                models.append(ModelInfo(
                    provider="openrouter",
                    model_id=m["id"],
                    display_name=m.get("name", m["id"]),
                    context_length=m.get("context_length", 0),
                    is_free=True,
                    raw=m,
                ))
        return models

    def _fetch_nvidia(self) -> list[ModelInfo]:
        """Liste les modèles NVIDIA (endpoint OpenAI-compatible)."""
        key = self._keys.get("nvidia")
        if not key:
            return []

        url = "https://integrate.api.nvidia.com/v1/models"
        headers = {"Authorization": f"Bearer {key}"}
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return []

        models = []
        for m in data.get("data", []):
            models.append(ModelInfo(
                provider="nvidia",
                model_id=m.get("id", ""),
                display_name=m.get("id", ""),
                context_length=0,
                is_free=True,
                raw=m,
            ))
        return models

    def _fetch_ollama(self) -> list[ModelInfo]:
        """Liste les modèles Ollama locaux."""
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        url = f"{host}/api/tags"
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return []

        models = []
        for m in data.get("models", []):
            models.append(ModelInfo(
                provider="ollama",
                model_id=m.get("name", ""),
                display_name=m.get("name", ""),
                context_length=0,
                is_free=True,
                raw=m,
            ))
        return models

    def pick_best_for(self, usage: str, provider: str | None = None) -> ModelInfo | None:
        """Choisit le meilleur modèle pour un usage donné.

        Args:
            usage: "code", "chat", "long_context", ...
            provider: filtre optionnel sur un provider

        Returns:
            Le meilleur ModelInfo, ou None si rien trouvé.
        """
        candidates = []
        providers = [provider] if provider else ["gemini", "groq", "openrouter", "nvidia"]

        for p in providers:
            for m in self.list_models(p):
                priority = MODEL_PRIORITIES.get(m.model_id, 0)
                if priority > 0:
                    candidates.append((priority, m))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    def all_free_models(self) -> list[ModelInfo]:
        """Retourne tous les modèles gratuits disponibles."""
        result = []
        for p in ["gemini", "groq", "openrouter", "nvidia", "ollama"]:
            result.extend([m for m in self.list_models(p) if m.is_free])
        return result


# Singleton
_registry: ModelRegistry | None = None


def get_registry() -> ModelRegistry:
    """Retourne le singleton du registre."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
