import os
import json
import httpx
from typing import Any, Dict, Optional
from core.providers.iresearch_provider import IResearchProvider
from core.secrets import load_secrets

class OllamaProvider(IResearchProvider):
    name: str = "ollama"

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        load_secrets()
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen3.5:9b")

    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        """Exécution 100% CPU pure (zéro VRAM, 12 threads physiques, streaming direct)."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": query,
            "stream": True,
            "options": {
                "num_gpu": 0,        # FORÇAGE : 0 couche en VRAM (GPU totalement ignoré)
                "num_thread": int(os.getenv("OLLAMA_NUM_THREAD", "12")),
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 150)
            }
        }
        
        timeout = httpx.Timeout(connect=10.0, read=180.0, write=10.0, pool=10.0)
        accumulated_text = []
        last_chunk = {}

        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        accumulated_text.append(chunk.get("response", ""))
                        if chunk.get("done", False):
                            last_chunk = chunk
                    except json.JSONDecodeError:
                        continue

        full_response = "".join(accumulated_text).strip()
        return {
            "provider": self.name,
            "model": self.model,
            "data": {
                "text": full_response,
                "raw": last_chunk
            }
        }
