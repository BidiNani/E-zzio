import httpx
from typing import Any, Dict, List
from core.providers.iresearch_provider import IResearchProvider
from core.secrets import load_secrets
import os

class JinaProvider(IResearchProvider):
    def __init__(self, api_key: str = None):
        load_secrets()
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        self.base_url = "https://s.jina.ai"

    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(
                f"{self.base_url}/",
                params={"q": query},
                headers=headers
            )
            resp.raise_for_status()
            
            data = resp.json()
            
            # Jina retourne {"code": 200, "status": 200, "data": [...]}
            results = data.get("data", [])
            
            return {
                "provider": "jina",
                "data": {
                    "results": results,
                    "total": len(results)
                }
            }
