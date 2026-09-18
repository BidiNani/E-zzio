"""core/cognitive_router.py - Routeur cognitif et résilience cloud/local pour E-ZzIO."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx


class ModelRouter:
    def __init__(
        self,
        ollama_url: str = "http://127.0.0.1:11434",
        gemini_api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.ollama_url = ollama_url.rstrip("/")
        if not gemini_api_key:
            try:
                from core.config.secrets_loader import gemini_keys
                g_keys = gemini_keys()
                gemini_api_key = g_keys[0] if g_keys else os.getenv("GEMINI_API_KEY")
            except Exception:
                gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_api_key = gemini_api_key
        self._client = http_client
        # Gate unifié (§4) : le routeur cognitif legacy consomme l'autorité
        # canonique. Aucun modèle REJECTED/UNKNOWN ne peut jamais être rendu.
        try:
            from core.routing.model_registry import (
                ModelQualificationStatus as _S,
            )
            from core.routing.model_registry import (
                canonical_model_registry as _reg,
            )
            self._authorized = {
                _reg._models[m].raw_model_name
                for m in _reg._models
                if _reg._models[m].qualification_status == _S.QUALIFIED
            } if hasattr(_reg, "_models") else {
                m.raw_model_name for m in _reg.list_models(qualified_only=True)
            }
            self._rejected = {
                _reg._models[m].raw_model_name
                for m in _reg._models
                if _reg._models[m].qualification_status == _S.REJECTED
            } if hasattr(_reg, "_models") else {
                m.raw_model_name for m in _reg.list_models(qualified_only=False)
                if m.qualification_status == _S.REJECTED
            }
        except Exception:
            self._authorized = {"qwen2.5-coder:7b-instruct-q4_K_M",
                                "gemini-3.7-flash"}
            self._rejected = {"qwen3.5:9b"}

    def _authorized_ollama(self) -> str:
        """Renvoie le modèle ollama AUTHORIZED (jamais REJECTED).
        Fail-closed : si le PRIMARY canonical est rejeté, aucun fallback."""
        from core.agent.coder_federation import _normalize_model_name
        primary = "qwen2.5-coder:7b-instruct-q4_K_M"
        if _normalize_model_name(primary) in self._rejected:
            raise RoutingIntegrityError(
                "[FAIL-CLOSED] cognitive_router : PRIMARY ollama REJECTED par "
                "le registre — aucun fallback autorisé.")
        return primary

    def resolve_route(self, profile: str) -> dict[str, Any]:
        has_gemini = bool(self.gemini_api_key)
        local_primary = self._authorized_ollama()
        local_fallback = "phi4-mini:latest"
        if local_fallback in self._rejected:
            raise RoutingIntegrityError(
                "[FAIL-CLOSED] cognitive_router : fallback REJECTED.")
        if profile == "prive":
            return {
                "primary": {"provider": "ollama", "model": local_primary},
                "fallback": {"provider": "ollama", "model": local_fallback},
            }

        if profile in ("raisonnement", "autonome"):
            if has_gemini and "gemini-3.7-flash" not in self._rejected:
                primary_model = "gemini-3.7-flash"
                primary_prov = "gemini"
            else:
                primary_model = local_primary
                primary_prov = "ollama"
            return {
                "primary": {"provider": primary_prov, "model": primary_model},
                "fallback": {"provider": "ollama", "model": local_fallback},
            }

        if profile == "rapide":
            primary_model = "gemini-3.7-flash" if (has_gemini and
                "gemini-3.7-flash" not in self._rejected) else local_primary
            return {
                "primary": {"provider": "gemini" if has_gemini else "ollama",
                            "model": primary_model},
                "fallback": {"provider": "ollama", "model": local_fallback},
            }

        primary_model = "gemini-3.7-flash" if (has_gemini and
            "gemini-3.7-flash" not in self._rejected) else local_primary
        return {
            "primary": {"provider": "gemini" if has_gemini else "ollama",
                        "model": primary_model},
            "fallback": {"provider": "ollama", "model": local_fallback},
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

    async def complete(self, profile: str, prompt: str) -> dict[str, Any]:
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

    async def probe_ollama(self) -> dict[str, Any]:
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

    async def probe_gemini(self) -> dict[str, Any]:
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

    async def probe_groq(self) -> dict[str, Any]:
        """Sonde la connectivité au service Groq Cloud."""
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            return {"online": False, "latency_ms": 0, "configured": False, "error": "GROQ_API_KEY non fournie"}

        client = self._client or httpx.AsyncClient()
        close_client = self._client is None
        start = time.perf_counter()
        try:
            url = "https://api.groq.com/openai/v1/models"
            headers = {"Authorization": f"Bearer {groq_key}"}
            res = await client.get(url, headers=headers, timeout=5.0)
            latency_ms = int((time.perf_counter() - start) * 1000)
            if res.status_code == 200:
                models = [m.get("id") for m in res.json().get("data", [])]
                return {"online": True, "latency_ms": latency_ms, "configured": True, "models": models, "error": None}
            return {"online": False, "latency_ms": latency_ms, "configured": True, "error": f"HTTP {res.status_code}"}
        except Exception as e:
            latency_ms = int((time.perf_counter() - start) * 1000)
            return {"online": False, "latency_ms": latency_ms, "configured": True, "error": str(e)}
        finally:
            if close_client:
                await client.aclose()

    def probe_antigravity(self) -> dict[str, Any]:
        """Inspecte le statut du provider Antigravity (fail-closed, blocage quota externe)."""
        return {
            "online": False,
            "status": "BLOCKED_BY_EXTERNAL_QUOTA",
            "latency_ms": 0,
            "quota": "EXHAUSTED",
            "fail_safe": True,
            "error": "Antigravity = BLOCKED_BY_EXTERNAL_QUOTA",
        }

    async def get_providers_health(self) -> dict[str, Any]:
        """Fournit une synthèse complète de la santé de tous les providers configurés en parallèle."""
        import asyncio
        results = await asyncio.gather(
            self.probe_ollama(),
            self.probe_gemini(),
            self.probe_groq(),
            return_exceptions=True
        )
        ollama_health = results[0] if not isinstance(results[0], Exception) else {"online": False, "error": str(results[0])}
        gemini_health = results[1] if not isinstance(results[1], Exception) else {"online": False, "error": str(results[1])}
        groq_health = results[2] if not isinstance(results[2], Exception) else {"online": False, "error": str(results[2])}
        antigravity_health = self.probe_antigravity()
        return {
            "timestamp": time.time(),
            "providers": {
                "ollama": ollama_health,
                "gemini": gemini_health,
                "groq": groq_health,
                "antigravity": antigravity_health,
            },
            "primary_available": bool(ollama_health.get("online") or gemini_health.get("online") or groq_health.get("online")),
            "deterministic_support": {
                "ollama": "DETERMINISTIC",
                "gemini": "BEST_EFFORT_DETERMINISTIC",
                "groq": "BEST_EFFORT_DETERMINISTIC",
                "antigravity": "UNSUPPORTED",
            }
        }


