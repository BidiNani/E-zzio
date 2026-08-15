import os
import httpx
from typing import Any, Dict, Optional
from core.providers.iresearch_provider import IResearchProvider
from core.secrets import load_secrets

class JinaProvider(IResearchProvider):
    name: str = "jina"

    def __init__(self, api_key: Optional[str] = None):
        load_secrets()
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        self.base_url = "https://s.jina.ai"

    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        headers = {
            "Accept": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(
                f"{self.base_url}/",
                params={"q": query},
                headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("data", [])

            return {
                "provider": self.name,
                "data": {
                    "results": results,
                    "total": len(results)
                }
            }
