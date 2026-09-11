"""
E-ZZIO Core — OpenRouter Cloud Provider (Coder Worker Federation).

Connecteur canonique conforme au contrat BaseProvider pour l'API OpenRouter
(https://openrouter.ai/api/v1/chat/completions).
Supporte inférence LLM, fallback généraliste, observabilité et gestion fail-closed.
Standard : Fail-Closed / Zéro fuite de credentials / Normalisation totale.
"""
from __future__ import annotations

import os
import json
import time
import logging
import httpx
from typing import Any, AsyncIterator, Dict, List, Optional

from core.secrets import load_secrets, get_api_key
from core.providers.base_provider import (
    BaseProvider,
    CostClass,
    ProviderAvailability,
    ProviderErrorClass,
    ProviderResponse,
)

logger = logging.getLogger("OpenRouterProvider")


class OpenRouterProvider(BaseProvider):
    """Fournisseur canonique OpenRouter conforme au contrat BaseProvider."""

    name: str = "openrouter"
    base_url: str = "https://openrouter.ai/api/v1"

    DEFAULT_LLM_MODEL: str = "meta-llama/llama-3.3-70b-instruct"
    DEFAULT_CODER_MODEL: str = "qwen/qwen-2.5-coder-32b-instruct"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        load_secrets()
        # Autorité credentials : core/security/unified_vault.py. Fallbacks compat conservés.
        # Fail-closed : une clé explicitement vide ("") désactive tout repli ambient.
        if api_key is not None:
            resolved_key = api_key
        else:
            resolved_key = None
            try:
                from core.security.unified_vault import key_vault
                resolved_key = key_vault.get_provider_key("openrouter") or None
            except Exception:
                resolved_key = None
            if not resolved_key:
                resolved_key = get_api_key("OPENROUTER_API_KEY")
            if not resolved_key:
                resolved_key = os.getenv("OPENROUTER_API_KEY")

        self.api_key = resolved_key.strip() if resolved_key else None
        self.model = model or self.DEFAULT_LLM_MODEL
        self.timeout = timeout

        if not self.api_key:
            self._status = ProviderAvailability.NOT_CONFIGURED
        else:
            self._status = ProviderAvailability.AVAILABLE

    def availability(self) -> ProviderAvailability:
        """Retourne l'état opérationnel du provider OpenRouter."""
        if not self.api_key:
            return ProviderAvailability.NOT_CONFIGURED
        return self._status

    def is_available(self) -> bool:
        """Vérifie si le provider est prêt pour des requêtes d'inférence."""
        return self.availability() in (ProviderAvailability.AVAILABLE, ProviderAvailability.DEGRADED)

    def cost_class(self, model: Optional[str] = None) -> CostClass:
        """OpenRouter est un endpoint cloud avec tarification token / free-tier."""
        if not self.api_key:
            return CostClass.UNKNOWN
        return CostClass.FREE_ENDPOINT

    def capabilities(self, model: Optional[str] = None) -> List[str]:
        """Retourne les capacités déduites pour le modèle demandé."""
        target = (model or self.model).lower()
        caps = ["TEXT", "INSTRUCTION_FOLLOWING"]
        if "coder" in target or "code" in target:
            caps.extend(["CODING", "REASONING"])
        if "llama" in target or "qwen" in target:
            caps.append("CODING")
        if "vision" in target:
            caps.extend(["VISION", "MULTIMODAL"])
        return sorted(list(set(caps)))

    async def health(self) -> Dict[str, Any]:
        """Vérifie la santé de l'endpoint OpenRouter sans fuite de secrets."""
        if not self.api_key:
            return {
                "status": "UNAVAILABLE",
                "error": "OPENROUTER_API_KEY non configurée",
                "available": False,
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://e-zzio.local",
            "X-Title": "E-ZZIO Sovereign Platform",
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/auth/key", headers=headers)
                if res.status_code == 200:
                    return {"status": "ONLINE", "available": True}
                elif res.status_code in (401, 403):
                    return {"status": "UNAUTHORIZED", "available": False, "error_code": res.status_code}
                return {"status": "DEGRADED", "available": False, "error_code": res.status_code}
        except Exception as exc:
            return {"status": "ERROR", "available": False, "error": str(exc)}

    def error_mapping(self, status_code: int, error_body: Optional[str] = None) -> ProviderErrorClass:
        """Mappe un code d'erreur HTTP vers la typologie canonique E-ZzIO."""
        if status_code in (401, 403):
            return ProviderErrorClass.UNAUTHORIZED
        elif status_code == 404:
            return ProviderErrorClass.MODEL_NOT_FOUND
        elif status_code == 429:
            return ProviderErrorClass.RATE_LIMITED
        elif status_code in (500, 502, 503, 504):
            return ProviderErrorClass.PROVIDER_UNAVAILABLE
        return ProviderErrorClass.UNKNOWN_ERROR

    def _map_http_error(self, status_code: int) -> ProviderErrorClass:
        return self.error_mapping(status_code)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> ProviderResponse:
        """Exécute une complétion via OpenRouter de façon fail-closed."""
        target_model = model or self.model

        if not self.api_key:
            return ProviderResponse(
                content="",
                model=target_model,
                provider=self.name,
                cost_class=CostClass.UNKNOWN,
                error_class=ProviderErrorClass.UNAUTHORIZED,
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://e-zzio.local",
            "X-Title": "E-ZZIO Sovereign Platform",
        }
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                latency = (time.perf_counter() - start_time) * 1000

                if res.status_code != 200:
                    err_class = self._map_http_error(res.status_code)
                    logger.warning("[OpenRouter] HTTP error %d (%s)", res.status_code, err_class.value)
                    return ProviderResponse(
                        content="",
                        model=target_model,
                        provider=self.name,
                        latency_ms=latency,
                        cost_class=self.cost_class(target_model),
                        error_class=err_class,
                    )

                data = res.json()
                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                usage = data.get("usage", {})

                return ProviderResponse(
                    content=content,
                    role="assistant",
                    model=target_model,
                    provider=self.name,
                    finish_reason=choice.get("finish_reason", "stop"),
                    usage=usage,
                    latency_ms=latency,
                    cost_class=self.cost_class(target_model),
                    error_class=None,
                    raw={"id": data.get("id"), "model": data.get("model")},
                )
        except httpx.TimeoutException:
            latency = (time.perf_counter() - start_time) * 1000
            return ProviderResponse(
                content="",
                model=target_model,
                provider=self.name,
                latency_ms=latency,
                cost_class=self.cost_class(target_model),
                error_class=ProviderErrorClass.TIMEOUT,
            )
        except Exception as exc:
            latency = (time.perf_counter() - start_time) * 1000
            logger.error("[OpenRouter] Unexpected exception: %s", exc)
            return ProviderResponse(
                content="",
                model=target_model,
                provider=self.name,
                latency_ms=latency,
                cost_class=self.cost_class(target_model),
                error_class=ProviderErrorClass.UNKNOWN_ERROR,
            )

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream de tokens via SSE OpenRouter."""
        target_model = model or self.model
        if not self.api_key:
            return

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://e-zzio.local",
            "X-Title": "E-ZZIO Sovereign Platform",
        }
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line or not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                        except Exception:
                            continue
        except Exception as exc:
            logger.error("[OpenRouter Stream] Error: %s", exc)
            return
