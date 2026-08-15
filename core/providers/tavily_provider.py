import httpx
from typing import Any, Dict
from core.providers.iresearch_provider import IResearchProvider

class TavilyProvider(IResearchProvider):
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.base_url = "https://api.tavily.com/search"

    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("Tavily API key required")
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        body = {"query": query, "max_results": 5}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(self.base_url, headers=headers, json=body)
            resp.raise_for_status()
            return {"provider": "tavily", "data": resp.json()}
