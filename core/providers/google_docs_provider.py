import os
from typing import Any

from core.providers.igoogle_provider import IGoogleProvider
from core.secrets import load_secrets


class GoogleDocsProvider(IGoogleProvider):
    def __init__(self, api_key: str = None):
        load_secrets()
        # Autorité credentials : core/security/unified_vault.py.
        try:
            from core.security.unified_vault import key_vault
            _vault_key = key_vault.get_provider_key("gemini") or None
        except Exception:
            _vault_key = None
        self.api_key = api_key or _vault_key or os.getenv("GEMINI_API_KEY")

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        # TODO: Implémenter l'appel à l'API Google Docs
        return {"provider": "google_docs", "data": {"status": "mock", "message": "GoogleDocsProvider not yet implemented"}}
