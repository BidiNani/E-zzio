import os
import httpx
from typing import Any
from core.models.discovery.base import ProviderDiscovery
from core.secrets import load_secrets

class OpenRouterDiscovery(ProviderDiscovery):
    provider = "openrouter"
    URL = "https://openrouter.ai/api/v1/models"

    def __init__(self, api_key: str | None = None):
        load_secrets()
        # Autorité credentials : core/security/unified_vault.py.
        vault_key = None
        try:
            from core.security.unified_vault import key_vault
            vault_key = key_vault.get_provider_key("openrouter") or None
        except Exception:
            vault_key = None
        self.api_key = api_key or vault_key or os.getenv("OPENROUTER_API_KEY")

    async def discover(self, api_key: str | None = None) -> list[dict[str, Any]]:
        headers = {"Content-Type": "application/json"}
        active_key = api_key or self.api_key
        if active_key and str(active_key).strip():
            headers["Authorization"] = f"Bearer {active_key.strip()}"

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(self.URL, headers=headers)
            response.raise_for_status()
            payload = response.json()

        result = []
        for raw in payload.get("data", []):
            model_id = raw.get("id")
            if not model_id:
                continue
            architecture = raw.get("architecture", {})
            result.append({
                "id": model_id,
                "provider": self.provider,
                "architecture": architecture,
                "raw": raw,
            })
        return result
