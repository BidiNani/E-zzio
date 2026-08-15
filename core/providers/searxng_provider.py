import httpx
from typing import Any, Dict
from core.providers.iresearch_provider import IResearchProvider

class SearXNGProvider(IResearchProvider):
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip("/")

    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/search", params={"q": query, "format": "json"})
            resp.raise_for_status()
            return {"provider": "searxng", "data": resp.json()}
