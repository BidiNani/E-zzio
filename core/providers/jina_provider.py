import httpx
from typing import Any, Dict
from core.providers.iresearch_provider import IResearchProvider

class JinaProvider(IResearchProvider):
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.base_url = "https://s.jina.ai"

    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(self.base_url, params={"q": query}, headers=headers)
            resp.raise_for_status()
            return {"provider": "jina", "data": resp.json()}
