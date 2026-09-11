import os
import httpx
from typing import Any
from core.models.discovery.base import ProviderDiscovery
from core.secrets import load_secrets

class GroqDiscovery(ProviderDiscovery):
    provider = "groq"
    URL = "https://api.groq.com/openai/v1/models"

    def __init__(self, api_key: str | None = None):
        load_secrets()
        # Autorité credentials : core/security/unified_vault.py.
        vault_key = None
        try:
            from core.security.unified_vault import key_vault
            vault_key = key_vault.get_provider_key("groq") or None
        except Exception:
            vault_key = None
        self.api_key = api_key or vault_key or os.getenv("GROQ_API_KEY")

    async def discover(self, api_key: str | None = None) -> list[dict[str, Any]]:
        headers = {"Content-Type": "application/json"}
        active_key = api_key or self.api_key
        if active_key and str(active_key).strip():
            headers["Authorization"] = f"Bearer {active_key.strip()}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(self.URL, headers=headers)
            response.raise_for_status()
            payload = response.json()

        if "data" not in payload:
            raw_data = []
        else:
            raw_data = payload.get("data")
            if raw_data is None:
                raise TypeError("Groq API contract violation: 'data' cannot be None")
            if not isinstance(raw_data, list):
                raise TypeError(f"Groq API contract violation: 'data' must be a list, got {type(raw_data).__name__}")

        result = []
        for raw in raw_data:
            if not isinstance(raw, dict):
                raise TypeError(f"Groq API contract violation: model item must be a dict, got {type(raw).__name__}")
            model_id = str(raw.get("id", ""))
            if not model_id:
                continue
            if any(sub in model_id.lower() for sub in ["whisper", "guard", "embed", "tts", "orpheus", "allam"]):
                continue
            result.append({
                "id": model_id,
                "provider": self.provider,
                "raw": raw,
            })
        return result
