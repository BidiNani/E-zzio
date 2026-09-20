import os
from typing import Any

from core.providers.igoogle_provider import IGoogleProvider
from core.secrets import load_secrets


class GoogleGmailProvider(IGoogleProvider):
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
        # [NOT_IMPLEMENTED] Ce provider est un stub.
        # Voir : https://github.com/BidiNani/E-zzio/issues
        raise NotImplementedError(
            "Ce provider n'est pas encore implémenté. "
            "Ouvrir une issue pour prioriser."
        )
        return {"provider": "google_gmail", "data": {"status": "mock", "message": "GoogleGmailProvider not yet implemented"}}
