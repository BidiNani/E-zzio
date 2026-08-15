import os
import httpx
from typing import Any, Dict, Optional, List
from core.providers.iresearch_provider import IResearchProvider
from core.secrets import load_secrets

class GeminiProvider(IResearchProvider):
    name: str = "gemini"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        load_secrets()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        """Exécute une recherche / synthèse textuelle via Gemini."""
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY manquante dans secrets/.env ou variables d'environnement")

        url = f"{self.base_url}/{self.model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }

        # Option d'activation de Google Search Grounding si demandé
        tools = kwargs.get("tools")
        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": query}]}]
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=35.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

            # Extraction du texte des candidats
            text_response = ""
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text_response = "".join(p.get("text", "") for p in parts)

            return {
                "provider": self.name,
                "model": self.model,
                "data": {
                    "text": text_response,
                    "raw": data
                }
            }
