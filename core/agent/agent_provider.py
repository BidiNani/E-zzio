"""E-ZZIO Autonomous Agent — Unified Router Bridge with Gemini 3.5 Flash-Lite & Auto-Purge."""
from __future__ import annotations
import os
import re
import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict, List
from core.security.unified_vault import key_vault
from core.models.router import EzzioRouter

os.environ["LITELLM_LOG"] = "ERROR"
logging.getLogger("LiteLLM").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


class AgentProviderAdapter:
    def __init__(self, backend: str = "cloud_gemini"):
        self.backend = backend
        self.router = self._build_canonical_router()

    def _build_canonical_router(self) -> EzzioRouter:
        gemini_key = key_vault.get_provider_key("gemini")
        if not gemini_key:
            logger.error("[VAULT-CRITICAL] Aucune clé Gemini trouvée dans le coffre-fort !")

        model_list = [
            {
                "model_name": "cloud_gemini",
                "litellm_params": {
                    "model": "gemini/gemini-3.5-flash-lite",
                    "api_key": gemini_key,
                },
            },
            {
                "model_name": "local_primary",
                "litellm_params": {
                    "model": "ollama/ezzio-granite",
                    "api_base": "http://127.0.0.1:11434",
                },
            },
            {
                "model_name": "local_fallback",
                "litellm_params": {
                    "model": "ollama/ornith-ezzio",
                    "api_base": "http://127.0.0.1:11434",
                },
            },
        ]
        return EzzioRouter(model_list=model_list)

    def _ensure_single_resident_model(self, target_ollama_model: str) -> None:
        """Décharge tout modèle Ollama actif qui n'est pas le modèle cible."""
        try:
            req_ps = urllib.request.Request("http://127.0.0.1:11434/api/ps", method="GET")
            with urllib.request.urlopen(req_ps, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                running_models = data.get("models", [])

            for item in running_models:
                m_name = item.get("name", "")
                if m_name and not target_ollama_model.startswith(m_name.split(":")[0]):
                    logger.info("[OLLAMA-AUTO-PURGE] Déchargement de la mémoire : %s", m_name)
                    unload_payload = json.dumps({"model": m_name, "keep_alive": 0}).encode("utf-8")
                    req_unload = urllib.request.Request(
                        "http://127.0.0.1:11434/api/generate",
                        data=unload_payload,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req_unload, timeout=3.0):
                        pass
        except Exception as exc:
            logger.debug("[OLLAMA-AUTO-PURGE] Contrôle ignoré : %s", exc)

    def _prepare_backend_memory(self, model_name: str) -> None:
        if model_name == "local_primary":
            self._ensure_single_resident_model("ezzio-granite")
        elif model_name == "local_fallback":
            self._ensure_single_resident_model("ornith-ezzio")

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        force_cloud: bool = False,
        speed: str = "fast"
    ) -> str:
        target_model = "cloud_gemini" if force_cloud else self.backend
        self._prepare_backend_memory(target_model)

        call_kwargs: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": 0.3,
        }
        if target_model.startswith("local_"):
            call_kwargs["think"] = False

        try:
            response = self.router.completion(**call_kwargs)
            return self._extract_content(response)
        except Exception as primary_exc:
            logger.warning("[ROUTER] Échec sur %s (%s). Repli automatique...", target_model, primary_exc)

            fallback_order = ["cloud_gemini", "local_primary", "local_fallback"]
            if target_model in fallback_order:
                fallback_order.remove(target_model)

            for fallback_model in fallback_order:
                self._prepare_backend_memory(fallback_model)
                fb_kwargs: Dict[str, Any] = {
                    "model": fallback_model,
                    "messages": messages,
                    "temperature": 0.3,
                }
                if fallback_model.startswith("local_"):
                    fb_kwargs["think"] = False

                try:
                    logger.info("[ROUTER] Tentative de repli sur %s...", fallback_model)
                    response = self.router.completion(**fb_kwargs)
                    return self._extract_content(response)
                except Exception as fb_exc:
                    logger.warning("[ROUTER] Échec du repli %s (%s)", fallback_model, fb_exc)

            raise RuntimeError(f"[FAIL-CLOSED] Tous les backends ont échoué : {primary_exc}")

    def _extract_content(self, response: Any) -> str:
        raw_text = ""
        if hasattr(response, "choices") and response.choices:
            choice = response.choices[0]
            if hasattr(choice, "message") and hasattr(choice.message, "content"):
                raw_text = choice.message.content or ""
        else:
            raw_text = str(response)

        cleaned = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()
        if "</think>" in cleaned:
            cleaned = cleaned.split("</think>")[-1].strip()

        return cleaned if cleaned else raw_text
