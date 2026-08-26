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
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen3:8b")

    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        """Exécution 100% CPU pure (zéro VRAM, 6 threads, thinking désactivé, budget tokens élevé)."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": query,
            "stream": True,
            "think": False,  # désactive le mode raisonnement (thinking) si supporté
            "options": {
                "num_gpu": 0,
                "num_thread": int(os.getenv("OLLAMA_NUM_THREAD", "6")),
                "num_ctx": kwargs.get("num_ctx", 2048),
                "num_predict": kwargs.get("max_tokens", 1500),  # budget relevé
                "temperature": kwargs.get("temperature", 0.7),
            },
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
                        token = chunk.get("response", "")
                        if token:
                            accumulated_text.append(token)
                        if chunk.get("done", False):
                            last_chunk = chunk
                    except json.JSONDecodeError:
                        continue

        full_response = "".join(accumulated_text).strip()

        # Ne jamais retourner de thinking brut. Si response est vide, c'est une génération tronquée.
        if not full_response:
            return {
                "provider": self.name,
                "model": self.model,
                "data": {
                    "text": "[Réponse tronquée : budget de tokens insuffisant pour ce modèle en mode raisonnement]",
                    "raw": last_chunk,
                },
            }

        return {"provider": self.name, "model": self.model, "data": {"text": full_response, "raw": last_chunk}}
