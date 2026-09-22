"""E-ZZIO Autonomous Agent — Unified Router Bridge with Strict Fail-Closed Boundaries."""
from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from typing import Any

from core.models.ezzio_router import EzzioRouter
from core.security.unified_vault import key_vault

os.environ["LITELLM_LOG"] = "ERROR"
logging.getLogger("LiteLLM").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


class RouteIntegrityError(RuntimeError):
    """Levée lorsqu'une route ou un modèle non autorisé/invalide est sollicité (Terminal)."""
    pass


class AgentProviderAdapter:
    AUTHORIZED_MODELS = {"cloud_gemini", "cloud_groq"}

    def __init__(self, backend: str = "cloud_gemini", local_model: str | None = None):
        self.backend = backend
        self.local_model = local_model
        self.router = self._build_canonical_router()

    def _build_canonical_router(self) -> EzzioRouter:
        gemini_key = key_vault.get_provider_key("gemini")
        if not gemini_key:
            logger.error("[VAULT-CRITICAL] Aucune clé Gemini trouvée dans le coffre-fort !")

        groq_key = key_vault.get_provider_key("groq")
        if not groq_key:
            logger.warning("[VAULT] Aucune clé Groq disponible pour le fallback cloud.")

        model_list = [
            {
                "model_name": "cloud_gemini",
                "litellm_params": {
                    "model": "gemini/gemini-3.7-flash",
                    "api_key": gemini_key,
                },
            },
            {
                "model_name": "cloud_groq",
                "litellm_params": {
                    "model": "groq/llama-3.3-70b-versatile",
                    "api_key": groq_key,
                },
            },
        ]
        return EzzioRouter(model_list=model_list)

    def _ensure_single_resident_model(self, target_ollama_model: str) -> None:
        """Décharge tout modèle Ollama actif qui n'est pas la cible sans masquer les pannes."""
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
            logger.error("[OLLAMA-AUTO-PURGE-FAIL] Démon Ollama injoignable pour la purge : %s", exc)
            raise ConnectionError(f"Démon Ollama injoignable pour l'isolation mémoire : {exc}") from exc

    def _prepare_backend_memory(self, model_name: str) -> None:
        if model_name == "local_primary":
            self._ensure_single_resident_model("ezzio-granite")
        elif model_name == "local_fallback":
            self._ensure_single_resident_model("ornith-ezzio")

    def _is_terminal_route_error(self, error: Exception) -> bool:
        """Détecte si l'erreur provient d'une route ou d'un modèle invalide (Fail-Closed)."""
        msg = str(error).lower()
        terminal_patterns = [
            "badrequesterror",
            "not found",
            "no healthy deployments",
            "model_not_found",
            "does not exist",
            "invalid model",
            "unknown model",
        ]
        return any(pat in msg for pat in terminal_patterns)

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        force_cloud: bool = False,
        speed: str = "fast"
    ) -> str:
        target_model = "cloud_gemini"

        if target_model not in self.AUTHORIZED_MODELS:
            raise RouteIntegrityError(
                f"[FAIL-CLOSED] Route ou modèle non autorisé : '{target_model}'. "
                f"Modèles autorisés : {self.AUTHORIZED_MODELS}"
            )

        # Master Chat est cloud-only ; aucune préparation Ollama.

        call_kwargs: dict[str, Any] = {
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
            if self._is_terminal_route_error(primary_exc):
                logger.error("[ROUTER-SECURITY] Erreur de route terminale sur %s : %s", target_model, primary_exc)
                raise RouteIntegrityError(
                    f"[FAIL-CLOSED] Rejet strict sur route invalide '{target_model}' : {primary_exc}"
                ) from primary_exc

            logger.warning("[ROUTER] Indisponibilité transitoire de %s (%s). Repli autorisé...", target_model, primary_exc)

            fallback_order = [m for m in ["cloud_groq"] if m != target_model]

            for fallback_model in fallback_order:
                # Fallback cloud : aucune préparation Ollama.
                fb_kwargs: dict[str, Any] = {
                    "model": fallback_model,
                    "messages": messages,
                    "temperature": 0.3,
                }
                if fallback_model.startswith("local_"):
                    fb_kwargs["think"] = False

                try:
                    logger.info("[ROUTER] Repli vers %s...", fallback_model)
                    response = self.router.completion(**fb_kwargs)
                    return self._extract_content(response)
                except Exception as fb_exc:
                    if self._is_terminal_route_error(fb_exc):
                        raise RouteIntegrityError(f"[FAIL-CLOSED] Route de repli invalide : {fb_exc}") from fb_exc
                    logger.warning("[ROUTER] Échec du repli %s (%s)", fallback_model, fb_exc)

            raise RuntimeError(f"[FAIL-CLOSED] Épuisement de tous les paliers autorisés : {primary_exc}") from primary_exc

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

