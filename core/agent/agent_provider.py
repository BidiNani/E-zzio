"""E-ZZIO Autonomous Agent — Compatibility Facade for Canonical Model Router & Provider Factory."""
from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import re
from typing import Any

from core.cognition.model_router import ModelRouter
from core.providers.base_provider import ProviderResponse
from core.providers.registry import ProviderFactory

logger = logging.getLogger(__name__)


class RouteIntegrityError(RuntimeError):
    """Levée lorsqu'une route ou un modèle non autorisé/invalide est sollicité (Terminal)."""
    pass


def _run_async(coro: Any) -> Any:
    """Exécute une coroutine de manière synchrone, compatible avec ou sans event loop actif."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


class AgentProviderAdapter:
    """Façade de compatibilité déléguant la décision et l'instanciation

    à la chaîne canonique : ModelRouter -> CanonicalModelRegistry -> ProviderFactory -> Provider.

    Phase 3B.1 : Zéro autorité autonome de routage (EzzioRouter / LiteLLM supprimés de ce composant).
    """

    AUTHORIZED_MODELS = {"cloud_gemini", "cloud_groq"}

    def __init__(self, backend: str = "cloud_gemini", local_model: str | None = None):
        self.backend = backend
        self.local_model = local_model
        self.router = ModelRouter()

    async def chat_completion_async(
        self,
        messages: list[dict[str, str]],
        force_cloud: bool = False,
        speed: str = "fast",
    ) -> str:
        """Version asynchrone déléguant à la chaîne canonique."""
        system_prompt = ""
        user_prompt = ""
        for m in messages:
            role = m.get("role", "")
            content = m.get("content", "")
            if role == "system":
                system_prompt = (system_prompt + "\n" + content).strip() if system_prompt else content
            elif role == "user":
                user_prompt = content

        if not user_prompt and messages:
            user_prompt = messages[-1].get("content", "")

        task_type = "coding" if speed == "coding" else "general"
        routing = self.router.select_engine(
            task_type=task_type,
            complexity_score=0.5 if speed == "fast" else 0.8,
            risk_level="low",
        )

        provider_name = routing.get("provider", "gemini")
        selected_model = routing.get("model", "gemini-3.7-flash")
        thinking_level = routing.get("thinking_level", "off")

        if force_cloud and provider_name == "ollama":
            provider_name = "gemini"
            selected_model = "gemini-3.7-flash"

        try:
            prov = ProviderFactory.create(provider_name)
            resp: ProviderResponse = await prov.generate(
                prompt=user_prompt,
                system_prompt=system_prompt if system_prompt else None,
                model=selected_model,
                thinking_level=thinking_level,
            )
            return self._extract_content(resp.content or "")
        except Exception as exc:
            logger.warning("[AgentProviderAdapter] Échec du provider %s -> fallback canonique : %s", provider_name, exc)
            try:
                fb_prov = ProviderFactory.create("gemini")
                resp = await fb_prov.generate(
                    prompt=user_prompt,
                    system_prompt=system_prompt if system_prompt else None,
                    model="gemini-3.5-flash-lite",
                )
                return self._extract_content(resp.content or "")
            except Exception as fb_exc:
                raise RuntimeError(f"[FAIL-CLOSED] Épuisement du fallback canonique : {fb_exc}") from fb_exc

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        force_cloud: bool = False,
        speed: str = "fast",
    ) -> str:
        """API publique synchrone de compatibilité pour CognitiveGateway / CodingAgentLoop."""
        return _run_async(self.chat_completion_async(messages, force_cloud=force_cloud, speed=speed))

    def chat(self, text: str = "", system_prompt: str = "", **kwargs: Any) -> dict[str, Any]:
        """API publique synchrone de compatibilité pour CodingAgentLoop."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if text:
            messages.append({"role": "user", "content": text})
        res_text = self.chat_completion(messages=messages)
        return {"response": res_text, "content": res_text, "ok": True}

    def _extract_content(self, response: Any) -> str:
        raw_text = str(response) if not isinstance(response, str) else response
        cleaned = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()
        if "</think>" in cleaned:
            cleaned = cleaned.split("</think>")[-1].strip()
        return cleaned if cleaned else raw_text
