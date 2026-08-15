import os
import httpx
from typing import Any, Dict, Optional
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
        """Exécute une requête de raisonnement / recherche avec Gemini."""
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY manquante dans secrets/.env ou variables d'environnement")

        # Strip 'models/' si présent pour éviter la duplication d'URL
        model_name = self.model.replace("models/", "")
        url = f"{self.base_url}/{model_name}:generateContent"
        
        params = {"key": self.api_key}
        headers = {"Content-Type": "application/json"}

        tools = kwargs.get("tools")
        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": query}]}]
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=35.0) as client:
            resp = await client.post(url, params=params, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

            text_response = ""
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text_response = "".join(p.get("text", "") for p in parts)

            return {
                "provider": self.name,
                "model": model_name,
                "data": {
                    "text": text_response,
                    "raw": data
                }
            }
