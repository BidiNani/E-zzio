from typing import Any, Dict
from core.providers.igoogle_provider import IGoogleProvider
from core.secrets import load_secrets
import os

class GoogleGmailProvider(IGoogleProvider):
    def __init__(self, api_key: str = None):
        load_secrets()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
    
    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        # TODO: Implémenter l'appel à l'API Gmail
        return {
            "provider": "google_gmail",
            "data": {"status": "mock", "message": "GoogleGmailProvider not yet implemented"}
        }
