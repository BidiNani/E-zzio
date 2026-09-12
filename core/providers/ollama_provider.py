"""
E-ZZIO Core — Ollama Local Provider (Phase 14 Hardening).

Connecteur canonique conforme au contrat BaseProvider et IResearchProvider pour le démon Ollama local
(http://127.0.0.1:11434).
Supporte inférence locale CPU/GPU, détection dynamique de disponibilité, streaming,
coût CostClass.LOCAL garanti à 0€ et compatibilité descendante totale avec IResearchProvider.search().
Standard : Fail-Closed / Zéro fuite / Mode Offline Souverain.
"""
from __future__ import annotations

import os
import json
import time
import asyncio
import logging
import httpx
from typing import Any, AsyncIterator, Dict, List, Optional

from core.secrets import load_secrets
from core.providers.iresearch_provider import IResearchProvider
from core.providers.base_provider import (
    BaseProvider,
    CostClass,
    ProviderAvailability,
    ProviderErrorClass,
    ProviderResponse,
)

logger = logging.getLogger("OllamaProvider")

_SHARED_CLIENT: httpx.AsyncClient | None = None


def _shared_client() -> httpx.AsyncClient:
    """Client httpx partagé (keepalive) : 0 handshake TLS/pool par appel."""
    global _SHARED_CLIENT
    if _SHARED_CLIENT is None or getattr(_SHARED_CLIENT, "is_closed", False) or not hasattr(_SHARED_CLIENT, "stream"):
        _SHARED_CLIENT = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=180.0, write=10.0, pool=10.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
    return _SHARED_CLIENT


class OllamaProvider(BaseProvider, IResearchProvider):
    """Fournisseur canonique Ollama conforme aux contrats BaseProvider et IResearchProvider."""

    name: str = "ollama"
    DEFAULT_MODEL: str = "qwen2.5-coder:7b-instruct-q4_K_M"

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
    ) -> None:
        load_secrets()
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", self.DEFAULT_MODEL)
        self.timeout = timeout

    def availability(self) -> ProviderAvailability:
        """Retourne l'état de disponibilité instantanée du démon Ollama local."""
        try:
            res = httpx.get(f"{self.base_url}/api/tags", timeout=1.5)
            if res.status_code == 200:
                return ProviderAvailability.AVAILABLE
            return ProviderAvailability.DEGRADED
        except Exception:
            return ProviderAvailability.UNAVAILABLE

    def is_available(self) -> bool:
        """Vérifie si le démon Ollama répond sur le réseau local."""
        return self.availability() in (ProviderAvailability.AVAILABLE, ProviderAvailability.DEGRADED)

    def cost_class(self, model: Optional[str] = None) -> CostClass:
        """Inférence locale = 0€ (LOCAL)."""
        return CostClass.LOCAL

    def capabilities(self, model: Optional[str] = None) -> List[str]:
        """Retourne les capacités déduites pour les modèles locaux."""
        target = (model or self.model).lower()
        caps = ["TEXT", "LOCAL", "INSTRUCTION_FOLLOWING"]
        if "vision" in target or "llava" in target:
            caps.extend(["VISION", "MULTIMODAL"])
        if "code" in target or "coder" in target:
            caps.append("CODING")
        if "r1" in target or "reason" in target or "qwen" in target:
            caps.extend(["REASONING", "CODING"])
        if "mini" in target or "nano" in target or "instant" in target:
            caps.append("FAST_INFERENCE")
        return sorted(list(set(caps)))

    def error_mapping(self, status_code: int, error_body: Optional[str] = None) -> ProviderErrorClass:
        """Mappe les statuts HTTP du serveur Ollama vers les classes canoniques."""
        if status_code == 404:
            return ProviderErrorClass.MODEL_NOT_FOUND
        elif status_code in (408, 504):
            return ProviderErrorClass.TIMEOUT
        elif status_code == 400:
            return ProviderErrorClass.BAD_REQUEST
        elif status_code in (500, 502, 503):
            return ProviderErrorClass.PROVIDER_UNAVAILABLE
        return ProviderErrorClass.UNKNOWN_ERROR

    async def health(self) -> Dict[str, Any]:
        """Vérifie la santé du démon Ollama et liste les modèles installés."""
        start_time = time.perf_counter()
        url = f"{self.base_url}/api/tags"
        try:
            res = await _shared_client().get(url, timeout=3.0)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            if res.status_code == 200:
                data = res.json()
                models = [m.get("name") for m in data.get("models", [])]
                return {
                    "status": "healthy",
                    "online": True,
                    "latency_ms": latency_ms,
                    "installed_models": models,
                    "provider": self.name,
                }
            else:
                return {
                    "status": "unhealthy",
                    "online": False,
                    "latency_ms": latency_ms,
                    "error": f"HTTP {res.status_code}",
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
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs: Any,
    ) -> ProviderResponse:
        """Exécute une inférence locale normalisée."""
        start_time = time.perf_counter()
        target_model = model or self.model
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": kwargs.get("keep_alive", "10m"),
            "think": kwargs.get("think", False),
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_thread": int(os.getenv("OLLAMA_NUM_THREAD", "6")),
                "num_ctx": kwargs.get("num_ctx", 2048),
            },
        }
        if system_prompt:
            payload["system"] = system_prompt
        else:
            from core.providers.base_provider import SYSTEM_IDENTITY as _IDENTITY
            payload["system"] = _IDENTITY

        try:
            timeout = httpx.Timeout(connect=5.0, read=self.timeout, write=5.0, pool=5.0)
            res = await _shared_client().post(url, json=payload, timeout=timeout)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            if res.status_code != 200:
                err_class = self.error_mapping(res.status_code, res.text)
                return ProviderResponse(
                    content="",
                    model=target_model,
                    provider=self.name,
                    latency_ms=latency_ms,
                    cost_class=CostClass.LOCAL,
                    error_class=err_class,
                    raw={"http_status": res.status_code, "text": res.text},
                )

            data = res.json()
            content = data.get("response", "").strip()
            if not content and data.get("thinking"):
                content = data.get("thinking", "").strip()
            prompt_eval = data.get("prompt_eval_count", 0)
            eval_count = data.get("eval_count", 0)

            return ProviderResponse(
                content=content,
                model=target_model,
                provider=self.name,
                finish_reason="stop" if data.get("done") else "length",
                usage={
                    "prompt_tokens": prompt_eval,
                    "completion_tokens": eval_count,
                    "total_tokens": prompt_eval + eval_count,
                },
                latency_ms=latency_ms,
                cost_class=CostClass.LOCAL,
                error_class=None,
                raw=data,
            )
        except httpx.ConnectError:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return ProviderResponse(
                content="",
                model=target_model,
                provider=self.name,
                latency_ms=latency_ms,
                cost_class=CostClass.LOCAL,
                error_class=ProviderErrorClass.PROVIDER_UNAVAILABLE,
                raw={"error": "Ollama local demon unreachable"},
            )
        except httpx.TimeoutException:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return ProviderResponse(
                content="",
                model=target_model,
                provider=self.name,
                latency_ms=latency_ms,
                cost_class=CostClass.LOCAL,
                error_class=ProviderErrorClass.TIMEOUT,
                raw={"error": "Ollama local inference timeout"},
            )
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return ProviderResponse(
                content="",
                model=target_model,
                provider=self.name,
                latency_ms=latency_ms,
                cost_class=CostClass.LOCAL,
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
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Diffuse les tokens au fil de leur génération locale."""
        target_model = model or self.model
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": True,
            "keep_alive": kwargs.get("keep_alive", "10m"),
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_thread": int(os.getenv("OLLAMA_NUM_THREAD", "6")),
            },
        }
        if system_prompt:
            payload["system"] = system_prompt
        else:
            from core.providers.base_provider import SYSTEM_IDENTITY as _IDENTITY
            payload["system"] = _IDENTITY

        timeout = httpx.Timeout(connect=5.0, read=self.timeout, write=5.0, pool=5.0)
        try:
            async with _shared_client().stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("response", "")
                            if token:
                                yield token
                            if chunk.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            logger.warning("[OLLAMA STREAM ERROR] %s", exc)

    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        """Méthode de recherche canonique compatible IResearchProvider."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": query,
            "stream": True,
            "keep_alive": kwargs.get("keep_alive", "10m"),
            "think": False,
            "options": {
                "num_gpu": 0,
                "num_thread": int(os.getenv("OLLAMA_NUM_THREAD", "6")),
                "num_ctx": kwargs.get("num_ctx", 2048),
                "num_predict": kwargs.get("max_tokens", 1500),
                "temperature": kwargs.get("temperature", 0.7),
            },
        }

        timeout = httpx.Timeout(connect=10.0, read=180.0, write=10.0, pool=10.0)
        accumulated_text = []
        last_chunk = {}

        async with _shared_client().stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        if token:
                            accumulated_text.append(token)
                        if chunk.get("done", False):
                            last_chunk = chunk
                    except json.JSONDecodeError:
                        continue

        full_response = "".join(accumulated_text).strip()

        if not full_response:
            return {
                "provider": self.name,
                "model": self.model,
                "data": {
                    "text": "[Réponse tronquée : budget de tokens insuffisant pour ce modèle en mode raisonnement]",
                    "raw": last_chunk,
                },
            }

        return {"provider": self.name, "model": self.model, "data": {"text": full_response, "raw": last_chunk}}
