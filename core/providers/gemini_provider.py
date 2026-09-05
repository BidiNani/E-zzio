"""
E-ZZIO Core — Gemini Cloud Provider (Phase 14 Hardening).

Connecteur canonique conforme au contrat BaseProvider et IResearchProvider pour l'API Google Gemini
(https://generativelanguage.googleapis.com/v1beta/models).
Supporte inférence LLM asynchrone, streaming SSE, configuration thinking (off/low/medium/high),
arbitrage de coût FREE_ENDPOINT et compatibilité descendante totale avec IResearchProvider.search().
Standard : Fail-Closed / Zéro fuite de credentials / Normalisation totale.
"""
from __future__ import annotations

import os
import json
import time
import asyncio
import logging
import httpx
from typing import Any, AsyncIterator, Dict, List, Optional

from core.secrets import load_secrets, get_api_key
from core.providers.iresearch_provider import IResearchProvider
from core.providers.base_provider import (
    BaseProvider,
    CostClass,
    ProviderAvailability,
    ProviderErrorClass,
    ProviderResponse,
)

logger = logging.getLogger("GeminiProvider")


class GeminiProvider(BaseProvider, IResearchProvider):
    """Fournisseur canonique Gemini conforme aux contrats BaseProvider et IResearchProvider."""

    name: str = "gemini"
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/models"
    DEFAULT_MODEL: str = "gemini-2.5-flash"
    FALLBACK_MODELS: List[str] = ["gemini-3.7-flash", "gemini-3.5-flash"]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 45.0,
    ) -> None:
        load_secrets()
        resolved_key = api_key if api_key is not None else get_api_key("GEMINI_API_KEY")
        if not resolved_key:
            resolved_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

        self.api_key = resolved_key.strip() if resolved_key else None
        self.model = model or os.getenv("GEMINI_MODEL", self.DEFAULT_MODEL)
        self.fallback_models = list(self.FALLBACK_MODELS)
        self.timeout = timeout

        if not self.api_key:
            self._status = ProviderAvailability.NOT_CONFIGURED
        else:
            self._status = ProviderAvailability.AVAILABLE

    def availability(self) -> ProviderAvailability:
        """Retourne l'état opérationnel actuel du fournisseur Gemini."""
        if not self.api_key:
            return ProviderAvailability.NOT_CONFIGURED
        return self._status

    def is_available(self) -> bool:
        """Vérifie si le provider est prêt pour des requêtes."""
        return self.availability() in (ProviderAvailability.AVAILABLE, ProviderAvailability.DEGRADED)

    def cost_class(self, model: Optional[str] = None) -> CostClass:
        """Endpoint Google AI Studio avec quota gratuit officiel."""
        if not self.api_key:
            return CostClass.UNKNOWN
        return CostClass.FREE_ENDPOINT

    def capabilities(self, model: Optional[str] = None) -> List[str]:
        """Retourne les capacités déduites pour les modèles Gemini."""
        target = (model or self.model).lower()
        caps = ["TEXT", "VISION", "MULTIMODAL", "INSTRUCTION_FOLLOWING"]
        if "flash" in target:
            caps.append("FAST_INFERENCE")
        if "pro" in target or "3.7" in target or "2.5" in target:
            caps.extend(["REASONING", "CODING", "TOOL_USE"])
        return sorted(list(set(caps)))

    def error_mapping(self, status_code: int, error_body: Optional[str] = None) -> ProviderErrorClass:
        """Mappe les statuts HTTP de l'API Google vers les classes canoniques."""
        if status_code in (401, 403):
            return ProviderErrorClass.UNAUTHORIZED
        elif status_code == 404:
            return ProviderErrorClass.MODEL_NOT_FOUND
        elif status_code in (408, 504):
            return ProviderErrorClass.TIMEOUT
        elif status_code == 409:
            return ProviderErrorClass.CONFLICT
        elif status_code == 429:
            return ProviderErrorClass.RATE_LIMITED
        elif status_code in (500, 502, 503):
            return ProviderErrorClass.PROVIDER_UNAVAILABLE
        elif status_code == 400:
            return ProviderErrorClass.BAD_REQUEST
        return ProviderErrorClass.UNKNOWN_ERROR

    def _build_generation_payload(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        thinking_level: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Construit la charge utile standard Gemini v1beta."""
        contents = [{"parts": [{"text": prompt}]}]
        payload: Dict[str, Any] = {"contents": contents}

        generation_config: Dict[str, Any] = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }

        # Configuration Thinking (Gemini 2.5 / 3.x)
        if thinking_level is not None:
            budget_map = {
                "off": 0,
                "low": 1024,
                "medium": 8192,
                "high": 24576,
            }
            budget = budget_map.get(str(thinking_level).lower(), 0)
            generation_config["thinkingConfig"] = {"thinkingBudget": budget}

        payload["generationConfig"] = generation_config

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        if "tools" in kwargs and kwargs["tools"]:
            payload["tools"] = kwargs["tools"]

        return payload

    async def health(self) -> Dict[str, Any]:
        """Vérifie la santé de l'API Gemini via listing des modèles."""
        start_time = time.perf_counter()
        if not self.api_key:
            self._status = ProviderAvailability.NOT_CONFIGURED
            return {
                "status": "not_configured",
                "online": False,
                "configured": False,
                "provider": self.name,
                "error": "GEMINI_API_KEY manquante",
            }

        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url)
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    self._status = ProviderAvailability.AVAILABLE
                    return {
                        "status": "healthy",
                        "online": True,
                        "latency_ms": latency_ms,
                        "models": models[:10],
                        "provider": self.name,
                    }
                else:
                    err_class = self.error_mapping(res.status_code, res.text)
                    if res.status_code in (401, 403):
                        self._status = ProviderAvailability.UNAUTHORIZED
                    elif res.status_code == 429:
                        self._status = ProviderAvailability.RATE_LIMITED
                    else:
                        self._status = ProviderAvailability.UNAVAILABLE
                    return {
                        "status": "unhealthy",
                        "online": False,
                        "latency_ms": latency_ms,
                        "error": f"HTTP {res.status_code}",
                        "error_class": err_class.value,
                        "provider": self.name,
                    }
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self._status = ProviderAvailability.UNAVAILABLE
            return {
                "status": "unhealthy",
                "online": False,
                "latency_ms": latency_ms,
                "error": str(exc),
                "provider": self.name,
            }

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        thinking_level: Optional[str] = None,
        **kwargs: Any,
    ) -> ProviderResponse:
        """Exécute une génération normalisée avec gestion d'erreurs."""
        start_time = time.perf_counter()
        target_model = (model or self.model).replace("models/", "")

        if not self.api_key:
            return ProviderResponse(
                content="",
                model=target_model,
                provider=self.name,
                cost_class=CostClass.UNKNOWN,
                error_class=ProviderErrorClass.UNAUTHORIZED,
                raw={"error": "GEMINI_API_KEY non configurée"},
            )

        payload = self._build_generation_payload(
            prompt=prompt,
            system_prompt=system_prompt,
            thinking_level=thinking_level,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        url = f"{self.base_url}/{target_model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, headers=headers, json=payload)
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                if res.status_code != 200:
                    err_class = self.error_mapping(res.status_code, res.text)
                    if res.status_code in (401, 403):
                        self._status = ProviderAvailability.UNAUTHORIZED
                    elif res.status_code == 429:
                        self._status = ProviderAvailability.RATE_LIMITED
                    return ProviderResponse(
                        content="",
                        model=target_model,
                        provider=self.name,
                        latency_ms=latency_ms,
                        cost_class=CostClass.FREE_ENDPOINT,
                        error_class=err_class,
                        raw={"http_status": res.status_code, "text": res.text},
                    )

                data = res.json()
                text_content = ""
                finish_reason = "stop"
                candidates = data.get("candidates", [])
                if candidates:
                    first = candidates[0]
                    parts = first.get("content", {}).get("parts", [])
                    text_content = "".join(p.get("text", "") for p in parts)
                    finish_reason = first.get("finishReason", "stop")

                usage_meta = data.get("usageMetadata", {})
                usage = {
                    "prompt_tokens": usage_meta.get("promptTokenCount", 0),
                    "completion_tokens": usage_meta.get("candidatesTokenCount", 0),
                    "total_tokens": usage_meta.get("totalTokenCount", 0),
                }

                return ProviderResponse(
                    content=text_content,
                    model=target_model,
                    provider=self.name,
                    finish_reason=finish_reason,
                    usage=usage,
                    latency_ms=latency_ms,
                    cost_class=CostClass.FREE_ENDPOINT,
                    error_class=None,
                    raw=data,
                )

        except httpx.TimeoutException:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return ProviderResponse(
                content="",
                model=target_model,
                provider=self.name,
                latency_ms=latency_ms,
                cost_class=CostClass.FREE_ENDPOINT,
                error_class=ProviderErrorClass.TIMEOUT,
                raw={"error": "Request timed out"},
            )
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return ProviderResponse(
                content="",
                model=target_model,
                provider=self.name,
                latency_ms=latency_ms,
                cost_class=CostClass.FREE_ENDPOINT,
                error_class=ProviderErrorClass.UNKNOWN_ERROR,
                raw={"error": str(exc)},
            )

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        thinking_level: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Diffuse les tokens au fil de la génération via streamGenerateContent."""
        target_model = (model or self.model).replace("models/", "")
        if not self.api_key:
            return

        payload = self._build_generation_payload(
            prompt=prompt,
            system_prompt=system_prompt,
            thinking_level=thinking_level,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        url = f"{self.base_url}/{target_model}:streamGenerateContent?alt=sse&key={self.api_key}"
        headers = {"Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        chunk_str = line[6:].strip()
                        if chunk_str == "[DONE]":
                            break
                        try:
                            data = json.loads(chunk_str)
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for p in parts:
                                    t = p.get("text", "")
                                    if t:
                                        yield t
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            logger.warning("[GEMINI STREAM ERROR] %s", exc)

    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        """Méthode de recherche canonique compatible IResearchProvider."""
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY manquante dans secrets/.env ou variables d'environnement")

        resp = await self.generate(prompt=query, **kwargs)
        if resp.error_class is not None:
            raise RuntimeError(f"Erreur Gemini Provider: {resp.error_class.value} - {resp.raw}")

        return {
            "provider": self.name,
            "model": resp.model,
            "data": {
                "text": resp.content,
                "model": resp.model,
                "raw": resp.raw or {},
            },
        }
