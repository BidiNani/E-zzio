import httpx
from typing import Any, Dict
from core.providers.iresearch_provider import IResearchProvider

class GeminiProvider(IResearchProvider):
    def __init__(self, api_key: str = None, model: str = "gemini-2.5-pro"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1/models"

    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("Gemini API key required")
        
        url = f"{self.base_url}/{self.model}:generateContent"
        headers = {"x-goog-api-key": self.api_key}
        body = {"contents": [{"parts": [{"text": query}]}]}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            return {"provider": "gemini", "data": resp.json()}
