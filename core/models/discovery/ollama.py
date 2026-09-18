from __future__ import annotations

import os
from typing import Any

import httpx

from core.models.discovery.base import ProviderDiscovery


class OllamaDiscovery(ProviderDiscovery):

    EMBEDDING_PATTERNS = {
        "embed",
        "embedding",
        "bge",
        "sentence-transformer",
        "sentence_transformers",
        "rerank",
        "reranker",
    }

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (
            base_url
            or os.environ.get(
                "OLLAMA_BASE_URL",
                "http://127.0.0.1:11434",
            )
        ).rstrip("/")

        self.provider = "ollama"

    @classmethod
    def _is_embedding_model(cls, model_id: str) -> bool:
        lowered = model_id.lower()
        return any(
            marker in lowered
            for marker in cls.EMBEDDING_PATTERNS
        )

    async def discover(
        self,
        api_key: str | None = None,
    ) -> list[dict[str, Any]]:

        del api_key

        url = f"{self.base_url}/api/tags"

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()

        models = payload.get("models", [])

        if not isinstance(models, list):
            raise TypeError(
                "Ollama API contract violation: models must be a list."
            )

        result: list[dict[str, Any]] = []

        for raw in models:

            if not isinstance(raw, dict):
                raise TypeError(
                    "Ollama API contract violation: "
                    "model item must be a dictionary."
                )

            model_id = str(raw.get("name", "")).strip()

            if not model_id:
                continue

            embedding = self._is_embedding_model(model_id)

            result.append(
                {
                    "model_id": model_id,
                    "provider": "ollama",
                    "display_name": model_id,
                    "execution_scope": "LOCAL",
                    "pricing_status": "NOT_APPLICABLE",
                    "pricing_source": "local_runtime",
                    "pricing": {
                        "prompt": 0.0,
                        "completion": 0.0,
                    },
                    "context_window": None,
                    "max_output_tokens": None,
                    "supports_chat": not embedding,
                    "supports_json": False,
                    "supports_tools": False,
                    "supports_reasoning": False,
                    "supports_embedding": embedding,
                    "raw": raw,
                }
            )

        return result
