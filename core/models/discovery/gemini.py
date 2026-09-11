"""Gemini dynamic model discovery with generation prioritization."""

from __future__ import annotations

import re
from typing import Any
import httpx

from .base import ProviderDiscovery


class GeminiDiscovery(ProviderDiscovery):

    provider = "gemini"
    URL = "https://generativelanguage.googleapis.com/v1beta/models"

    EXCLUDED_PATTERNS = (
        "tts",
        "embed",
        "aqa",
        "imagen",
        "vision-preview",
    )

    @staticmethod
    def _version_rank(model_id: str) -> float:
        """Attribue un score d'ordre selon la génération du modèle."""
        match = re.search(r"gemini-(\d+(?:\.\d+)?)", model_id.lower())
        if match:
            return float(match.group(1))
        return 1.0

    async def discover(
        self,
        api_key: str,
    ) -> list[dict[str, Any]]:

        headers = {
            "x-goog-api-key": api_key,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                self.URL,
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()

        result = []

        for raw in payload.get("models", []):
            name = str(raw.get("name", ""))
            if not name:
                continue

            model_id = name.split("models/", 1)[-1]

            if any(p in model_id.lower() for p in self.EXCLUDED_PATTERNS):
                continue

            methods = {str(x) for x in raw.get("supportedGenerationMethods", [])}
            if not methods & {"generateContent", "generateMessage"}:
                continue

            result.append(
                {
                    "model_id": model_id,
                    "display_name": raw.get("displayName") or model_id,
                    "context_window": raw.get("inputTokenLimit", 128000),
                    "max_output_tokens": raw.get("outputTokenLimit"),
                    "supports_chat": True,
                    "supports_json": True,
                    "supports_tools": True,
                    "supports_reasoning": "thinking" in model_id.lower() or "pro" in model_id.lower(),
                    "version_rank": self._version_rank(model_id),
                }
            )

        # Tri par version décroissante (les modèles les plus récents en premier) [non vérifié]
        result.sort(key=lambda x: (x["version_rank"], "flash" in x["model_id"]), reverse=True)
        return result
