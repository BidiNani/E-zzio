"""
Client LLM 100% Google Gemini Ultra-Haute Vitesse & Streaming SSE pour E-ZzIO.
Optimisations actives :
1. thinking_config: {"thinking_budget": 0} (Suppression du temps de réflexion pré-génération)
2. streamGenerateContent?alt=sse (Streaming réel token-par-token)
3. Transport HTTP/1.1 sécurisé
"""

import json
import logging
from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
from langchain_core.messages import HumanMessage, SystemMessage

from ezzio.config import settings
from ezzio.llm.circuit_breaker import CircuitBreaker

logger = logging.getLogger("EzzioLLMClient")


def _get_gemini_api_key() -> str | None:
    """Récupère la clé API Google Gemini valide dans secrets/.env ou settings."""
    env_paths = [
        Path("G:/AI/E-zzio/secrets/.env"),
        Path("secrets/.env"),
        Path(__file__).resolve().parent.parent.parent.parent / "secrets" / ".env"
    ]
    for p in env_paths:
        if p.exists():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "GEMINI_API_KEY=" in line:
                        k, v = line.split("=", 1)
                        clean_v = v.strip().strip("\"'")
                        if clean_v and clean_v.startswith("AIzaSy"):
                            return clean_v
            except Exception:
                pass
    return settings.gemini_api_key


class HybridLLMClient:
    def __init__(self) -> None:
        self.api_key = _get_gemini_api_key()
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=15.0)

        # Modèles Gemini officiels 3.x supportés (sans modèles 2.x dépréciés)
        self.online_gemini_models = [
            "gemini-3.7-flash",
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-3.1-pro-preview",
            "gemini-3.6-flash",
        ]

    def _build_payload(self, prompt: str, system_prompt: str, temperature: float, disable_thinking: bool = True) -> dict:
        gen_config = {
            "temperature": temperature,
            "maxOutputTokens": 4096,
        }
        if disable_thinking:
            gen_config["thinking_config"] = {"thinking_budget": 0}

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": str(prompt)}]
                }
            ],
            "generationConfig": gen_config
        }
        if system_prompt:
            payload["system_instruction"] = {
                "parts": [{"text": str(system_prompt)}]
            }
        return payload

    async def ainvoke(
        self,
        prompt: str,
        system_prompt: str = "Tu es E-ZZIO, âme numérique souveraine et assistant technique d'élite conçu par BidiNani.",
        temperature: float = 0.2,
        model: str | None = None
    ) -> tuple[str, str]:
        """
        Exécute la requête sur Google Gemini avec thinking_budget=0 pour un premier token instantané.
        """
        if not self.api_key:
            return "Erreur : Clé GEMINI_API_KEY absente.", "error"

        requested = [model] if model else []
        candidates = requested + [m for m in self.online_gemini_models if m not in requested]

        last_error = ""
        for target_model in candidates:
            if not target_model:
                continue
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={self.api_key}"
            payload = self._build_payload(prompt, system_prompt, temperature, disable_thinking=True)

            try:
                async with httpx.AsyncClient(
                    http2=False,
                    timeout=httpx.Timeout(connect=5.0, read=45.0, write=5.0, pool=5.0),
                    limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
                ) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates_list = data.get("candidates", [])
                        if candidates_list and "content" in candidates_list[0]:
                            parts = candidates_list[0]["content"].get("parts", [])
                            if parts and "text" in parts[0]:
                                self.circuit_breaker.record_success()
                                return parts[0]["text"].strip(), f"{target_model} (Google Cloud Gemini)"
                    elif resp.status_code == 429:
                        logger.warning("[GEMINI 429] Quota atteint sur %s -> Essai immédiat modèle suivant...", target_model)
                        last_error = "Quota temporaire atteint (429)."
                    elif resp.status_code == 404:
                        logger.warning("Modèle %s non trouvé (404) -> Essai modèle suivant...", target_model)
                        last_error = f"Modèle {target_model} non trouvé."
                    else:
                        logger.warning("Gemini %s HTTP %d", target_model, resp.status_code)
                        last_error = f"HTTP {resp.status_code}"
            except Exception as exc:
                logger.warning("Erreur connexion Gemini (%s) : %s", target_model, exc)
                last_error = str(exc)

        # Repli local uniquement si Cloud inaccessible
        logger.warning("[FALLBACK] Bascule locale vers Ollama 127.0.0.1:11434...")
        self.circuit_breaker.record_failure("Cloud inaccessible")
        try:
            from langchain_ollama import ChatOllama
            local_llm = ChatOllama(
                model=settings.local_core_model,
                base_url="http://127.0.0.1:11434",
                temperature=0.1,
                timeout=10.0
            )
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]
            res = await local_llm.ainvoke(messages)
            content = res.content if hasattr(res, "content") else str(res)
            return content.strip(), f"{settings.local_core_model} (Local Fallback)"
        except Exception as local_exc:
            logger.error("Échec local : %s", local_exc)

        return f"Erreur Gemini Cloud : {last_error}", "error"

    async def astream(
        self,
        prompt: str,
        system_prompt: str = "Tu es E-ZZIO, âme numérique souveraine et assistant technique d'élite conçu par BidiNani.",
        temperature: float = 0.2,
        model: str | None = None
    ) -> AsyncGenerator[str, None]:
        """
        Streaming réel token-par-token via l'endpoint officiel streamGenerateContent?alt=sse.
        """
        if not self.api_key:
            yield "Erreur : Clé GEMINI_API_KEY absente."
            return

        target_model = model or settings.cloud_model_primary
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:streamGenerateContent?alt=sse&key={self.api_key}"
        payload = self._build_payload(prompt, system_prompt, temperature, disable_thinking=True)

        try:
            async with httpx.AsyncClient(
                http2=False,
                timeout=httpx.Timeout(connect=5.0, read=60.0, write=5.0, pool=5.0)
            ) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        yield f"Erreur Gemini HTTP {response.status_code}"
                        return
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if line.startswith("data:"):
                            raw_json = line[5:].strip()
                            if raw_json and raw_json != "[DONE]":
                                try:
                                    chunk = json.loads(raw_json)
                                    candidates = chunk.get("candidates", [])
                                    if candidates and "content" in candidates[0]:
                                        parts = candidates[0]["content"].get("parts", [])
                                        for part in parts:
                                            if "text" in part:
                                                yield part["text"]
                                except Exception:
                                    pass
        except Exception as exc:
            logger.error("Erreur de streaming Gemini : %s", exc)
            yield f"\n[Erreur de streaming : {str(exc)}]"


_GLOBAL_CLIENT: HybridLLMClient | None = None


def get_llm_client() -> HybridLLMClient:
    global _GLOBAL_CLIENT
    if _GLOBAL_CLIENT is None:
        _GLOBAL_CLIENT = HybridLLMClient()
    return _GLOBAL_CLIENT
