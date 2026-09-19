"""
E-ZZIO Core — Groq Cloud Provider (Phase 6B).

Connecteur canonique conforme au contrat BaseProvider pour l'API Groq Cloud
(https://api.groq.com/openai/v1).
Supporte inférence LLM asynchrone non-bloquante, streaming SSE, rotation multi-clés SovereignKeyPool
et compatibilité avec le système de fédération cognitive.
Standard : Fail-Closed / Zéro fuite de credentials / Observabilité / Déterminisme.
"""
from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from core.cognition.providers.key_pool import SovereignKeyPool
from core.providers.base_provider import (
    BaseProvider,
    CostClass,
    ProviderAvailability,
    ProviderErrorClass,
    ProviderResponse,
)
from core.providers.iresearch_provider import IResearchProvider
from core.secrets import get_api_key, load_secrets

logger = logging.getLogger("GroqProvider")


class GroqProvider(BaseProvider, IResearchProvider):
    """Fournisseur canonique Groq Cloud conforme au contrat BaseProvider."""

    name: str = "groq"
    base_url: str = "https://api.groq.com/openai/v1"
    DEFAULT_MODEL: str = "llama-3.3-70b-versatile"
    FALLBACK_MODELS: list[str] = ["llama-3.1-8b-instant", "mixtral-8x7b-32768"]

    def __init__(
        self,
        api_key: str | None = None,
        key_pool: SovereignKeyPool | None = None,
        model: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        load_secrets()
        self.model = model or os.getenv("GROQ_MODEL", self.DEFAULT_MODEL)
        self.timeout = timeout

        if key_pool is not None:
            self.key_pool = key_pool
        else:
            # Autorité credentials : vault, puis secrets_loader (DISCORD_GROQ_API_KEY
            # prioritaire), puis variables indexées. Pool 403 constaté 2026-09-10 :
            # rotation conservée pour le jour de rétablissement.
            keys: list[str] = []
            try:
                from core.security.unified_vault import key_vault
                for vk in key_vault.get_all_keys_for_provider("groq"):
                    if vk and vk.strip() and vk.strip() not in keys:
                        keys.append(vk.strip())
            except Exception:
                pass
            try:
                from core.config.secrets_loader import groq_key as _loader_groq_key
                _lk = (_loader_groq_key() or "").strip()
                if _lk and _lk not in keys:
                    keys.insert(0, _lk)
            except Exception:
                pass
            primary = api_key or get_api_key("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
            if primary and primary.strip():
                keys.append(primary.strip())
            for i in range(1, 20):
                k = get_api_key(f"GROQ_API_KEY_{i}") or os.getenv(f"GROQ_API_KEY_{i}")
                if k and k.strip() and k.strip() not in keys:
                    keys.append(k.strip())

            self.key_pool = SovereignKeyPool(provider_name="groq", raw_keys=keys)

        self._status = ProviderAvailability.AVAILABLE if self.key_pool.slots else ProviderAvailability.NOT_CONFIGURED

    def _get_active_key(self) -> tuple[int | None, str | None, str | None]:
        return self.key_pool.get_next_key()

    def availability(self) -> ProviderAvailability:
        """Retourne l'état opérationnel actuel basé sur la santé du pool de clés."""
        if not self.key_pool.slots:
            return ProviderAvailability.NOT_CONFIGURED

        now = time.time()
        active_count = 0
        rate_limited_count = 0
        auth_failed_count = 0

        for slot in self.key_pool.slots:
            status_val = getattr(slot.status, "value", str(slot.status))
            if status_val in ("RATE_LIMITED", "QUOTA_EXHAUSTED", "TEMPORARILY_UNAVAILABLE"):
                if now >= slot.blocked_until:
                    active_count += 1
                else:
                    rate_limited_count += 1
            elif status_val == "AUTH_FAILED":
                auth_failed_count += 1
            elif status_val == "AVAILABLE":
                active_count += 1

        if active_count > 0:
            return ProviderAvailability.AVAILABLE
        elif rate_limited_count > 0:
            return ProviderAvailability.RATE_LIMITED
        elif auth_failed_count == len(self.key_pool.slots):
            return ProviderAvailability.UNAUTHORIZED
        return ProviderAvailability.UNAVAILABLE

    def is_available(self) -> bool:
        """Vérifie si au moins une clé est prête pour des requêtes d'inférence."""
        return self.availability() in (ProviderAvailability.AVAILABLE, ProviderAvailability.DEGRADED)

    def cost_class(self, model: str | None = None) -> CostClass:
        """Endpoint Cloud Groq gratuit (Free Tier LPUs)."""
        if not self.key_pool.slots:
            return CostClass.UNKNOWN
        return CostClass.FREE_ENDPOINT

    def capabilities(self, model: str | None = None) -> list[str]:
        """Retourne les capacités déduites pour le modèle cible."""
        target = (model or self.model).lower()
        caps = ["TEXT", "CODING", "FAST_INFERENCE", "INSTRUCTION_FOLLOWING"]
        if "vision" in target or "vlm" in target:
            caps.extend(["VISION", "MULTIMODAL"])
        return caps

    def error_mapping(self, status_code: int, _error_body: str | None = None) -> ProviderErrorClass:
        """Mappe les codes HTTP vers la typologie canonique E-ZzIO."""
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

    async def health(self) -> dict[str, Any]:
        """Vérifie la santé de l'endpoint Groq Cloud via /models."""
        start_time = time.perf_counter()
        idx, raw_key, masked_key = self._get_active_key()
        if raw_key is None:
            return {
                "status": "not_configured",
                "online": False,
                "configured": False,
                "provider": self.name,
                "error": "Aucune clé Groq active disponible",
            }

        url = f"{self.base_url}/models"
        headers = {
            "Authorization": f"Bearer {raw_key}",
            "User-Agent": "E-ZZIO-Sovereign-Core/9.4",
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url, headers=headers)
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("id") for m in data.get("data", [])]
                    self.key_pool.mark_success(idx)
                    return {
                        "status": "healthy",
                        "online": True,
                        "latency_ms": latency_ms,
                        "models": models,
                        "provider": self.name,
                        "active_slot": masked_key,
                    }
                else:
                    err_class = self.error_mapping(res.status_code, res.text)
                    if res.status_code == 429:
                        self.key_pool.mark_rate_limited(idx, ttl_seconds=60.0, error_code=429)
                    elif res.status_code in (401, 403):
                        self.key_pool.mark_auth_failed(idx, error_code=res.status_code)
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
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs: Any,
    ) -> ProviderResponse:
        """Exécute une inférence asynchrone non-bloquante avec rotation de clé sur 429."""
        start_time = time.perf_counter()
        target_model = model or self.model
        url = f"{self.base_url}/chat/completions"

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        max_attempts = len(self.key_pool.slots) if self.key_pool.slots else 1

        for _ in range(max_attempts):
            idx, raw_key, masked_key = self._get_active_key()
            if raw_key is None:
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return ProviderResponse(
                    content="",
                    role="assistant",
                    model=target_model,
                    provider=self.name,
                    latency_ms=latency_ms,
                    cost_class=CostClass.FREE_ENDPOINT,
                    error_class=ProviderErrorClass.RATE_LIMITED,
                    raw={"error": "All Groq keys exhausted or rate-limited."},
                )

            headers = {
                "Authorization": f"Bearer {raw_key}",
                "Content-Type": "application/json",
                "User-Agent": "E-ZZIO-Sovereign-Core/9.4",
            }

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    res = await client.post(url, headers=headers, json=payload)
                    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                    if res.status_code == 429:
                        self.key_pool.mark_rate_limited(idx, ttl_seconds=60.0, error_code=429)
                        logger.warning("[GROQ] Slot %s rate-limited (429). Rotation...", masked_key)
                        continue

                    if res.status_code in (401, 403):
                        self.key_pool.mark_auth_failed(idx, error_code=res.status_code)
                        logger.error("[GROQ] Slot %s invalid auth (%d). Rotation...", masked_key, res.status_code)
                        continue

                    if res.status_code != 200:
                        err_class = self.error_mapping(res.status_code, res.text)
                        return ProviderResponse(
                            content="",
                            role="assistant",
                            model=target_model,
                            provider=self.name,
                            latency_ms=latency_ms,
                            cost_class=CostClass.FREE_ENDPOINT,
                            error_class=err_class,
                            raw={"status_code": res.status_code, "error": res.text, "masked_key": masked_key},
                        )

                    data = res.json()
                    self.key_pool.mark_success(idx)

                    choices = data.get("choices", [])
                    content = choices[0].get("message", {}).get("content", "") if choices else ""
                    finish_reason = choices[0].get("finish_reason", "stop") if choices else None
                    usage = data.get("usage", {})

                    return ProviderResponse(
                        content=content,
                        role="assistant",
                        model=target_model,
                        provider=self.name,
                        finish_reason=finish_reason,
                        usage={
                            "prompt_tokens": usage.get("prompt_tokens", 0),
                            "completion_tokens": usage.get("completion_tokens", 0),
                            "total_tokens": usage.get("total_tokens", 0),
                        },
                        latency_ms=latency_ms,
                        cost_class=CostClass.FREE_ENDPOINT,
                        error_class=None,
                        raw={"masked_key": masked_key, "data": data},
                    )

            except httpx.TimeoutException:
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return ProviderResponse(
                    content="",
                    role="assistant",
                    model=target_model,
                    provider=self.name,
                    latency_ms=latency_ms,
                    cost_class=CostClass.FREE_ENDPOINT,
                    error_class=ProviderErrorClass.TIMEOUT,
                )
            except Exception as exc:
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return ProviderResponse(
                    content="",
                    role="assistant",
                    model=target_model,
                    provider=self.name,
                    latency_ms=latency_ms,
                    cost_class=CostClass.FREE_ENDPOINT,
                    error_class=ProviderErrorClass.PROVIDER_UNAVAILABLE,
                    raw={"exception": str(exc)},
                )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return ProviderResponse(
            content="",
            role="assistant",
            model=target_model,
            provider=self.name,
            latency_ms=latency_ms,
            cost_class=CostClass.FREE_ENDPOINT,
            error_class=ProviderErrorClass.RATE_LIMITED,
            raw={"error": "Groq rotation exhausted all keys."},
        )

    async def stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Diffuse les tokens au fil de leur génération via le streaming SSE Groq."""
        target_model = model or self.model
        url = f"{self.base_url}/chat/completions"

        idx, raw_key, masked_key = self._get_active_key()
        if raw_key is None:
            return

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {raw_key}",
            "Content-Type": "application/json",
            "User-Agent": "E-ZZIO-Sovereign-Core/9.4",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    line_data = line[6:].strip()
                    if line_data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(line_data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

    async def search(self, query: str, **kwargs: Any) -> dict[str, Any]:
        """Exécute une inférence / recherche compatible DecisionRouter."""
        resp = await self.generate(
            prompt=query,
            model=kwargs.get("model", self.DEFAULT_MODEL),
            max_tokens=kwargs.get("max_tokens", 512),
            temperature=kwargs.get("temperature", 0.2),
        )
        if resp.error_class is not None:
            raise RuntimeError(f"Groq error ({resp.error_class.value}): {resp.raw}")
        return {
            "provider": self.name,
            "model": resp.model,
            "data": {
                "text": resp.content,
                "model": resp.model,
                "usage": resp.usage,
                "raw": resp.raw,
            }
        }

