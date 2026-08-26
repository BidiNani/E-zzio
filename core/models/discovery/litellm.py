"""LiteLLM gateway discovery."""

from __future__ import annotations

import os
from typing import Any
import httpx

from .base import ProviderDiscovery


class LiteLLMDiscovery(ProviderDiscovery):

    provider = "litellm"

    async def discover(
        self,
        api_key: str,
    ) -> list[dict[str, Any]]:

        base_url = os.environ.get(
            "EZZIO_LITELLM_BASE_URL",
            "http://127.0.0.1:4000",
        ).rstrip("/")

        url = f"{base_url}/v1/models"
        headers: dict[str, str] = {}

        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                url,
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()

        result = []

        for raw in payload.get("data", []):
            model_id = raw.get("id")

            if not model_id:
                continue

            result.append(
                {
                    "model_id": model_id,
                    "display_name": model_id,
                    "context_window": None,
                    "max_output_tokens": None,
                    "supports_chat": True,
                    "supports_json": True,
                    "supports_tools": True,
                    "supports_reasoning": "reason" in model_id.lower(),
                    "gateway": base_url,
                }
            )

        return result