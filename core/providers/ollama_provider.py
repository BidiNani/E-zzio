import httpx
from typing import Any, Dict, Optional
from core.providers.iresearch_provider import IResearchProvider
from core.secrets import load_secrets
import os

class OllamaProvider(IResearchProvider):
    name: str = "ollama"

    def __init__(self, model: str = None, base_url: str = None):
        load_secrets()
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": query,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
        
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            
            data = resp.json()
            text = data.get("response", "").strip()
            
            return {
                "provider": self.name,
                "model": self.model,
                "data": {
                    "text": text,
                    "model": self.model
                }
            }
