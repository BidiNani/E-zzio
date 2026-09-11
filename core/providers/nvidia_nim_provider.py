"""
E-ZZIO Core — NVIDIA NIM Provider (Phase 5B).

Connecteur canonique conforme au contrat BaseProvider pour l'API NVIDIA NIM
(https://integrate.api.nvidia.com/v1).
Supporte inférence LLM, streaming, multimodalité vision et gestion fail-closed.
Standard : Fail-Closed / Zéro fuite de credentials / Normalisation totale.
"""
from __future__ import annotations

import os
import json
import base64
import time
import logging
import httpx
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from core.secrets import load_secrets, get_api_key
from core.providers.base_provider import (
    BaseProvider,
    CostClass,
    ProviderAvailability,
    ProviderErrorClass,
    ProviderResponse,
)

logger = logging.getLogger("NvidiaNimProvider")


class NvidiaNimProvider(BaseProvider):
    """Fournisseur canonique NVIDIA NIM conforme au contrat BaseProvider."""

    name: str = "NVIDIA"
    base_url: str = "https://integrate.api.nvidia.com/v1"

    DEFAULT_LLM_MODEL: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    DEFAULT_VISION_MODEL: str = "meta/llama-3.2-11b-vision-instruct"
    DEFAULT_IMAGE_MODEL: str = "stabilityai/stable-diffusion-xl"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 30.0):
        load_secrets()
        # Autorité credentials : core/security/unified_vault.py. Fallbacks compat conservés.
        # Fail-closed : une clé explicitement vide ("") désactive tout repli ambient.
        if api_key is not None:
            resolved_key = api_key
        else:
            resolved_key = None
            try:
                from core.security.unified_vault import key_vault
                resolved_key = key_vault.get_provider_key("nvidia") or None
            except Exception:
                resolved_key = None
            if not resolved_key:
                resolved_key = get_api_key("NVIDIA_API_KEY")
            if not resolved_key:
                resolved_key = os.getenv("NVIDIA_API_KEY")

        self.api_key = resolved_key.strip() if resolved_key else None
        self.timeout = timeout

        if not self.api_key:
            self._status = ProviderAvailability.NOT_CONFIGURED
        else:
            self._status = ProviderAvailability.AVAILABLE

    def availability(self) -> ProviderAvailability:
        """Retourne l'état opérationnel du provider NVIDIA."""
        if not self.api_key:
            return ProviderAvailability.NOT_CONFIGURED
        return self._status

    def is_available(self) -> bool:
        """Vérifie si le provider est prêt pour des requêtes d'inférence."""
        return self.availability() in (ProviderAvailability.AVAILABLE, ProviderAvailability.DEGRADED)

    def cost_class(self, model: Optional[str] = None) -> CostClass:
        """Politique de coût E-ZzIO : FREE_ENDPOINT pour le quota d'évaluation Build."""
        if not self.api_key:
            return CostClass.UNKNOWN
        return CostClass.FREE_ENDPOINT

    def capabilities(self, model: Optional[str] = None) -> List[str]:
        """Retourne les capacités déduites pour le modèle cible."""
        target = (model or self.DEFAULT_LLM_MODEL).lower()
        if "vision" in target or "vlm" in target or "fuyu" in target:
            return ["TEXT", "VISION", "MULTIMODAL"]
        if "code" in target or "codestral" in target:
            return ["TEXT", "CODING", "TOOL_USE"]
        if "reason" in target or "pro" in target or "70b" in target:
            return ["TEXT", "REASONING", "TOOL_USE", "AGENTIC"]
        if "embed" in target:
            return ["EMBEDDING"]
        return ["TEXT", "INSTRUCTION_FOLLOWING", "TOOL_USE"]

    def error_mapping(self, status_code: int, error_body: Optional[str] = None) -> ProviderErrorClass:
        """Mappe les statuts HTTP de l'API NVIDIA vers les classes d'erreurs canoniques."""
        if status_code in (401, 403):
            return ProviderErrorClass.UNAUTHORIZED
        elif status_code in (404, 410):
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

    async def health(self) -> Dict[str, Any]:
        """Sonde de santé de l'API NVIDIA NIM (catalogue public ou auth)."""
        if self.availability() == ProviderAvailability.NOT_CONFIGURED:
            return {
                "provider": self.name,
                "status": ProviderAvailability.NOT_CONFIGURED.value,
                "healthy": False,
                "message": "NVIDIA_API_KEY non configurée dans SecretsVault"
            }

        start = time.perf_counter()
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/models", headers=headers)
                latency_ms = (time.perf_counter() - start) * 1000
                if resp.status_code == 200:
                    self._status = ProviderAvailability.AVAILABLE
                    return {
                        "provider": self.name,
                        "status": ProviderAvailability.AVAILABLE.value,
                        "healthy": True,
                        "latency_ms": round(latency_ms, 2)
                    }
                else:
                    err_cls = self.error_mapping(resp.status_code)
                    if err_cls == ProviderErrorClass.UNAUTHORIZED:
                        self._status = ProviderAvailability.UNAUTHORIZED
                    elif err_cls == ProviderErrorClass.RATE_LIMITED:
                        self._status = ProviderAvailability.RATE_LIMITED
                    else:
                        self._status = ProviderAvailability.DEGRADED
                    return {
                        "provider": self.name,
                        "status": self._status.value,
                        "healthy": False,
                        "error_class": err_cls.value,
                        "status_code": resp.status_code,
                        "latency_ms": round(latency_ms, 2)
                    }
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            self._status = ProviderAvailability.UNAVAILABLE
            return {
                "provider": self.name,
                "status": ProviderAvailability.UNAVAILABLE.value,
                "healthy": False,
                "error_class": ProviderErrorClass.TIMEOUT.value if isinstance(e, httpx.TimeoutException) else ProviderErrorClass.PROVIDER_UNAVAILABLE.value
            }

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs: Any
    ) -> ProviderResponse:
        """Exécute une inférence synchrone et retourne un ProviderResponse normalisé."""
        if self.availability() == ProviderAvailability.NOT_CONFIGURED:
            raise RuntimeError("[FAIL-CLOSED] NVIDIA_API_KEY manquante dans SecretsVault")

        target_model = model or self.DEFAULT_LLM_MODEL
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                latency_ms = (time.perf_counter() - start) * 1000

                if resp.status_code != 200:
                    err_cls = self.error_mapping(resp.status_code, resp.text)
                    if err_cls == ProviderErrorClass.UNAUTHORIZED:
                        self._status = ProviderAvailability.UNAUTHORIZED
                    elif err_cls == ProviderErrorClass.RATE_LIMITED:
                        self._status = ProviderAvailability.RATE_LIMITED
                    else:
                        self._status = ProviderAvailability.DEGRADED

                    return ProviderResponse(
                        content="",
                        role="assistant",
                        model=target_model,
                        provider=self.name,
                        finish_reason="error",
                        usage={},
                        latency_ms=round(latency_ms, 2),
                        cost_class=self.cost_class(target_model),
                        error_class=err_cls,
                        raw={"status_code": resp.status_code, "body": resp.text[:200]}
                    )

                try:
                    data = resp.json()
                except Exception as json_err:
                    return ProviderResponse(
                        content="",
                        role="assistant",
                        model=target_model,
                        provider=self.name,
                        finish_reason="malformed_response",
                        usage={},
                        latency_ms=round(latency_ms, 2),
                        cost_class=self.cost_class(target_model),
                        error_class=ProviderErrorClass.PROVIDER_UNAVAILABLE,
                        raw={"status_code": 200, "malformed_reason": "INVALID_JSON", "body": resp.text[:200]}
                    )

                self._status = ProviderAvailability.AVAILABLE

                choices = data.get("choices")
                if not choices or not isinstance(choices, list) or len(choices) == 0:
                    return ProviderResponse(
                        content="",
                        role="assistant",
                        model=target_model,
                        provider=self.name,
                        finish_reason="malformed_response",
                        usage=data.get("usage", {}),
                        latency_ms=round(latency_ms, 2),
                        cost_class=self.cost_class(target_model),
                        error_class=ProviderErrorClass.PROVIDER_UNAVAILABLE,
                        raw={"status_code": 200, "malformed_reason": "EMPTY_CHOICES", "data": data}
                    )

                c0 = choices[0]
                content = c0.get("message", {}).get("content", "")
                role = c0.get("message", {}).get("role", "assistant")
                finish_reason = c0.get("finish_reason", "stop")

                if not content or (isinstance(content, str) and not content.strip()):
                    return ProviderResponse(
                        content="",
                        role=role,
                        model=target_model,
                        provider=self.name,
                        finish_reason="malformed_response",
                        usage=data.get("usage", {}),
                        latency_ms=round(latency_ms, 2),
                        cost_class=self.cost_class(target_model),
                        error_class=ProviderErrorClass.PROVIDER_UNAVAILABLE,
                        raw={"status_code": 200, "malformed_reason": "EMPTY_CONTENT", "finish_reason": finish_reason}
                    )

                usage = data.get("usage", {})

                return ProviderResponse(
                    content=content,
                    role=role,
                    model=target_model,
                    provider=self.name,
                    finish_reason=finish_reason,
                    usage=usage,
                    latency_ms=round(latency_ms, 2),
                    cost_class=self.cost_class(target_model),
                    error_class=None,
                    raw=data
                )

        except httpx.TimeoutException:
            self._status = ProviderAvailability.DEGRADED
            latency_ms = (time.perf_counter() - start) * 1000
            return ProviderResponse(
                content="",
                role="assistant",
                model=target_model,
                provider=self.name,
                finish_reason="timeout",
                usage={},
                latency_ms=round(latency_ms, 2),
                cost_class=self.cost_class(target_model),
                error_class=ProviderErrorClass.TIMEOUT,
                raw={"error": "Client timeout exceeded"}
            )
        except Exception as e:
            self._status = ProviderAvailability.UNAVAILABLE
            latency_ms = (time.perf_counter() - start) * 1000
            return ProviderResponse(
                content="",
                role="assistant",
                model=target_model,
                provider=self.name,
                finish_reason="error",
                usage={},
                latency_ms=round(latency_ms, 2),
                cost_class=self.cost_class(target_model),
                error_class=ProviderErrorClass.UNKNOWN_ERROR,
                raw={"error": str(type(e).__name__)}
            )

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs: Any
    ) -> AsyncIterator[str]:
        """Diffuse les tokens en continu (Server-Sent Events) depuis NVIDIA NIM."""
        if self.availability() == ProviderAvailability.NOT_CONFIGURED:
            raise RuntimeError("[FAIL-CLOSED] NVIDIA_API_KEY manquante dans SecretsVault")

        target_model = model or self.DEFAULT_LLM_MODEL
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "text/event-stream",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }

        timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", f"{self.base_url}/chat/completions", headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[len("data:"):].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Méthode de rétrocompatibilité renvoyant la structure de dictionnaire historique."""
        resp = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        if resp.error_class:
            raise RuntimeError(f"NVIDIA API error: {resp.error_class.value}")
        return {
            "provider": "nvidia_nim",
            "model": resp.model,
            "content": resp.content,
            "usage": resp.usage,
            "raw": resp.raw
        }

    async def analyze_image(
        self,
        prompt: str,
        image_path: str | Path,
        model: Optional[str] = None,
        max_tokens: int = 256,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Inférence multimodale / vision sur image locale."""
        if self.availability() == ProviderAvailability.NOT_CONFIGURED:
            raise RuntimeError("[FAIL-CLOSED] NVIDIA_API_KEY manquante dans SecretsVault")

        img_p = Path(image_path).resolve()
        if not img_p.exists():
            raise FileNotFoundError(f"Image source introuvable: {img_p}")

        img_b64 = base64.b64encode(img_p.read_bytes()).decode("utf-8")
        ext = img_p.suffix.lower().lstrip(".") or "png"
        mime = f"image/{ext}" if ext in ["png", "jpeg", "jpg", "webp"] else "image/png"
        data_uri = f"data:{mime};base64,{img_b64}"

        target_model = model or self.DEFAULT_VISION_MODEL
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        payload = {
            "model": target_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_uri}}
                    ]
                }
            ],
            "max_tokens": max_tokens
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            resp.raise_for_status()
            data = resp.json()

        content = ""
        usage = {}
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0].get("message", {}).get("content", "")
        if "usage" in data:
            usage = data["usage"]

        return {
            "provider": "nvidia_nim",
            "model": target_model,
            "content": content,
            "usage": usage,
            "raw": data
        }

    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        """Exécute une inférence / recherche compatible DecisionRouter."""
        resp = await self.generate(
            prompt=query,
            model=kwargs.get("model", self.DEFAULT_LLM_MODEL),
            max_tokens=kwargs.get("max_tokens", 512),
            temperature=kwargs.get("temperature", 0.2),
        )
        if resp.error_class is not None:
            raise RuntimeError(f"NVIDIA NIM error ({resp.error_class.value}): {resp.raw}")
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

