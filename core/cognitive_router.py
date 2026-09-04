"""core/cognitive_router.py - Routeur cognitif et résilience cloud/local pour E-ZzIO."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional
import httpx


class ModelRouter:
    def __init__(
        self,
        ollama_url: str = "http://127.0.0.1:11434",
        gemini_api_key: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.ollama_url = ollama_url.rstrip("/")
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self._client = http_client

    def resolve_route(self, profile: str) -> Dict[str, Any]:
        has_gemini = bool(self.gemini_api_key)

        if profile == "prive":
            return {
                "primary": {"provider": "ollama", "model": "qwen3.5:9b"},
                "fallback": {"provider": "ollama", "model": "phi4-mini:latest"},
            }

        if profile in ("raisonnement", "autonome"):
            primary_prov = "gemini" if has_gemini else "ollama"
            primary_model = "gemini-3.8-flash" if has_gemini else "qwen3.5:9b"
            return {
                "primary": {"provider": primary_prov, "model": primary_model},
                "fallback": {"provider": "ollama", "model": "qwen3.5:9b"},
            }

        if profile == "rapide":
            primary_prov = "gemini" if has_gemini else "ollama"
            primary_model = "gemini-2.5-flash" if has_gemini else "phi4-mini:latest"
            return {
                "primary": {"provider": primary_prov, "model": primary_model},
                "fallback": {"provider": "ollama", "model": "phi4-mini:latest"},
            }

        primary_prov = "gemini" if has_gemini else "ollama"
        primary_model = "gemini-2.5-flash" if has_gemini else "qwen3.5:9b"
        return {
            "primary": {"provider": primary_prov, "model": primary_model},
            "fallback": {"provider": "ollama", "model": "phi4-mini:latest"},
        }

    async def _call_ollama(self, client: httpx.AsyncClient, model: str, prompt: str) -> str:
        res = await client.post(
            f"{self.ollama_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=30.0,
        )
        res.raise_for_status()
        return res.json().get("response", "")

    async def _call_gemini(self, client: httpx.AsyncClient, model: str, prompt: str) -> str:
        if not self.gemini_api_key:
            raise ValueError("Clé GEMINI_API_KEY absente.")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={self.gemini_api_key}"
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        res = await client.post(url, json=payload, timeout=30.0)
        res.raise_for_status()
        data = res.json()
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "")
        return ""

    async def complete(self, profile: str, prompt: str) -> Dict[str, Any]:
        routes = self.resolve_route(profile)
        primary = routes["primary"]
        fallback = routes["fallback"]

        client = self._client or httpx.AsyncClient()
        close_client = self._client is None

        try:
            try:
                if primary["provider"] == "gemini":
                    text = await self._call_gemini(client, primary["model"], prompt)
                else:
                    text = await self._call_ollama(client, primary["model"], prompt)
                return {
                    "text": text,
                    "provider_used": primary["provider"],
                    "model_used": primary["model"],
                    "fallback_triggered": False,
                }
            except Exception as primary_err:
                if fallback["provider"] == "ollama":
                    text = await self._call_ollama(client, fallback["model"], prompt)
                else:
                    text = await self._call_gemini(client, fallback["model"], prompt)

                return {
                    "text": text,
                    "provider_used": fallback["provider"],
                    "model_used": fallback["model"],
                    "fallback_triggered": True,
                    "primary_error": str(primary_err),
                }
        finally:
            if close_client:
                await client.aclose()

    async def probe_ollama(self) -> Dict[str, Any]:
        """Sonde l'état de santé du serveur Ollama local."""
        client = self._client or httpx.AsyncClient()
        close_client = self._client is None
        start = time.perf_counter()
        try:
            res = await client.get(f"{self.ollama_url}/api/tags", timeout=3.0)
            latency_ms = int((time.perf_counter() - start) * 1000)
            if res.status_code == 200:
                models = [m.get("name") for m in res.json().get("models", [])]
                return {"online": True, "latency_ms": latency_ms, "models": models, "error": None}
            return {"online": False, "latency_ms": latency_ms, "models": [], "error": f"HTTP {res.status_code}"}
        except Exception as e:
            latency_ms = int((time.perf_counter() - start) * 1000)
            return {"online": False, "latency_ms": latency_ms, "models": [], "error": str(e)}
        finally:
            if close_client:
                await client.aclose()

    async def probe_gemini(self) -> Dict[str, Any]:
        """Sonde la connectivité au service Gemini Cloud."""
        if not self.gemini_api_key:
            return {"online": False, "latency_ms": 0, "configured": False, "error": "GEMINI_API_KEY non fournie"}

        client = self._client or httpx.AsyncClient()
        close_client = self._client is None
        start = time.perf_counter()
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.gemini_api_key}"
            res = await client.get(url, timeout=5.0)
            latency_ms = int((time.perf_counter() - start) * 1000)
            if res.status_code == 200:
                return {"online": True, "latency_ms": latency_ms, "configured": True, "error": None}
            return {"online": False, "latency_ms": latency_ms, "configured": True, "error": f"HTTP {res.status_code}"}
        except Exception as e:
            latency_ms = int((time.perf_counter() - start) * 1000)
            return {"online": False, "latency_ms": latency_ms, "configured": True, "error": str(e)}
        finally:
            if close_client:
                await client.aclose()

    async def get_providers_health(self) -> Dict[str, Any]:
        """Fournit une synthèse complète de la santé de tous les providers configurés."""
        ollama_health = await self.probe_ollama()
        gemini_health = await self.probe_gemini()
        return {
            "timestamp": time.time(),
            "providers": {
                "ollama": ollama_health,
                "gemini": gemini_health,
            },
            "primary_available": ollama_health["online"] or gemini_health["online"],
        }

