import os
import httpx
from typing import Any, Dict, Optional
from core.providers.iresearch_provider import IResearchProvider
from core.secrets import load_secrets

class OllamaProvider(IResearchProvider):
    name: str = "ollama"

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        load_secrets()
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:latest")

    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        """Exécute une inférence locale souveraine via Ollama."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": query,
            "stream": False
        }
        timeout = kwargs.get("timeout", 60.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            response_text = data.get("response", "").strip()

            return {
                "provider": self.name,
                "model": self.model,
                "data": {
                    "text": response_text,
                    "raw": data
                }
            }
