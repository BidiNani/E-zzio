"""E-ZZIO Core — Providers unifiés pour coder_worker.

Chaque provider interroge le ``ModelRegistry`` pour trouver le
meilleur modèle disponible **au moment de l'appel**, sans liste
codée en dur.

**Providers** :
- ``GeminiProvider`` : Gemini 3.8 Flash et suivants
- ``GroqProvider`` : Qwen 3.8 27B et suivants
- ``OpenRouterProvider`` : GLM-5.2, Cohere North, etc.
- ``NvidiaProvider`` : Nemotron
- ``OllamaProvider`` : local
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

from core.coding.model_registry import ModelInfo, get_registry

logger = logging.getLogger(__name__)


@dataclass
class ProviderResponse:
    success: bool
    content: str = ""
    model_used: str = ""
    provider: str = ""
    error: str = ""
    raw: dict[str, Any] | None = None


class BaseProvider:
    """Provider de base. À hériter."""

    name: str = "base"
    api_key_env: str = ""

    def __init__(self):
        self.api_key = os.environ.get(self.api_key_env, "")

    def is_available(self) -> bool:
        if self.name == "ollama":
            return True
        return bool(self.api_key)

    def pick_model(self) -> ModelInfo | None:
        raise NotImplementedError

    def call(self, prompt: str, model_id: str | None = None, **kwargs) -> ProviderResponse:
        raise NotImplementedError


class GeminiProvider(BaseProvider):
    name = "gemini"
    api_key_env = "GEMINI_API_KEY"

    def pick_model(self) -> ModelInfo | None:
        return get_registry().pick_best_for("code", provider="gemini")

    def call(self, prompt: str, model_id: str | None = None, **kwargs) -> ProviderResponse:
        if not self.api_key:
            return ProviderResponse(success=False, error="GEMINI_API_KEY absent", provider=self.name)

        if not model_id:
            m = self.pick_model()
            if not m:
                return ProviderResponse(success=False, error="Aucun modèle Gemini disponible", provider=self.name)
            model_id = m.model_id

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.2),
                "maxOutputTokens": kwargs.get("max_tokens", 4096),
            },
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            content = data["candidates"][0]["content"]["parts"][0]["text"]
            return ProviderResponse(
                success=True, content=content,
                model_used=model_id, provider=self.name, raw=data,
            )
        except Exception as exc:
            return ProviderResponse(success=False, error=str(exc), provider=self.name)


class GroqProvider(BaseProvider):
    name = "groq"
    api_key_env = "GROQ_API_KEY"

    def pick_model(self) -> ModelInfo | None:
        return get_registry().pick_best_for("code", provider="groq")

    def call(self, prompt: str, model_id: str | None = None, **kwargs) -> ProviderResponse:
        if not self.api_key:
            return ProviderResponse(success=False, error="GROQ_API_KEY absent", provider=self.name)

        if not model_id:
            m = self.pick_model()
            if not m:
                return ProviderResponse(success=False, error="Aucun modèle Groq disponible", provider=self.name)
            model_id = m.model_id

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.2),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            content = data["choices"][0]["message"]["content"]
            return ProviderResponse(
                success=True, content=content,
                model_used=model_id, provider=self.name, raw=data,
            )
        except Exception as exc:
            return ProviderResponse(success=False, error=str(exc), provider=self.name)


class OpenRouterProvider(BaseProvider):
    name = "openrouter"
    api_key_env = "OPENROUTER_API_KEY"

    def pick_model(self) -> ModelInfo | None:
        return get_registry().pick_best_for("code", provider="openrouter")

    def call(self, prompt: str, model_id: str | None = None, **kwargs) -> ProviderResponse:
        if not model_id:
            m = self.pick_model()
            if not m:
                return ProviderResponse(success=False, error="Aucun modèle OpenRouter free disponible", provider=self.name)
            model_id = m.model_id

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        headers["HTTP-Referer"] = "https://github.com/BidiNani/E-zzio"
        headers["X-Title"] = "E-zzio coder_worker"

        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.2),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            content = data["choices"][0]["message"]["content"]
            return ProviderResponse(
                success=True, content=content,
                model_used=model_id, provider=self.name, raw=data,
            )
        except Exception as exc:
            return ProviderResponse(success=False, error=str(exc), provider=self.name)


class NvidiaProvider(BaseProvider):
    name = "nvidia"
    api_key_env = "NVIDIA_API_KEY"

    def pick_model(self) -> ModelInfo | None:
        return get_registry().pick_best_for("code", provider="nvidia")

    def call(self, prompt: str, model_id: str | None = None, **kwargs) -> ProviderResponse:
        if not self.api_key:
            return ProviderResponse(success=False, error="NVIDIA_API_KEY absent", provider=self.name)

        if not model_id:
            m = self.pick_model()
            if not m:
                return ProviderResponse(success=False, error="Aucun modèle NVIDIA disponible", provider=self.name)
            model_id = m.model_id

        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.2),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            content = data["choices"][0]["message"]["content"]
            return ProviderResponse(
                success=True, content=content,
                model_used=model_id, provider=self.name, raw=data,
            )
        except Exception as exc:
            return ProviderResponse(success=False, error=str(exc), provider=self.name)


# Factory
def get_provider(name: str) -> BaseProvider | None:
    """Retourne un provider par nom."""
    providers = {
        "gemini": GeminiProvider,
        "groq": GroqProvider,
        "openrouter": OpenRouterProvider,
        "nvidia": NvidiaProvider,
    }
    cls = providers.get(name.lower())
    return cls() if cls else None


def get_all_available() -> list[BaseProvider]:
    """Retourne tous les providers disponibles, dans l'ordre de priorité.

    Ordre optimisé pour le free tier :
    1. Groq — rapide (< 1s), quotas généreux
    2. Gemini — qualité mais quota limité (429 fréquents)
    3. OpenRouter — fallback diversifié
    4. NVIDIA — fallback final
    """
    result = []
    for name in ["groq", "gemini", "openrouter", "nvidia"]:
        p = get_provider(name)
        if p and p.is_available():
            result.append(p)
    return result
