import os
import asyncio
import httpx
from typing import Any, Dict, Optional, List
from core.providers.iresearch_provider import IResearchProvider
from core.secrets import load_secrets

class GeminiProvider(IResearchProvider):
    name: str = "gemini"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        load_secrets()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
        # Modèles de secours par ordre de priorité
        self.fallback_models = ["gemini-3.6-flash", "gemini-2.5-flash"]
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    async def _call_endpoint(self, client: httpx.AsyncClient, model_name: str, payload: Dict[str, Any]) -> httpx.Response:
        url = f"{self.base_url}/{model_name}:generateContent"
        params = {"key": self.api_key}
        headers = {"Content-Type": "application/json"}
        return await client.post(url, params=params, headers=headers, json=payload)

    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        """Exécute une requête avec retry automatique et basculement de modèle."""
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY manquante dans secrets/.env ou variables d'environnement")

        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": query}]}]
        }
        if "tools" in kwargs and kwargs["tools"]:
            payload["tools"] = kwargs["tools"]

        # Liste ordonnée des modèles à tester
        models_to_try = [self.model.replace("models/", "")]
        for fb in self.fallback_models:
            clean_fb = fb.replace("models/", "")
            if clean_fb not in models_to_try:
                models_to_try.append(clean_fb)

        last_error = None

        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
            for current_model in models_to_try:
                # 2 tentatives avec backoff par modèle
                for attempt in range(1, 3):
                    try:
                        resp = await self._call_endpoint(client, current_model, payload)
                        
                        # Si surcharge (503/429), pause et nouvelle tentative
                        if resp.status_code in (503, 429, 500):
                            await asyncio.sleep(1.0 * attempt)
                            continue
                            
                        resp.raise_for_status()
                        data = resp.json()

                        text_response = ""
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            text_response = "".join(p.get("text", "") for p in parts)

                        return {
                            "provider": self.name,
                            "model": current_model,
                            "data": {
                                "text": text_response,
                                "model": current_model,
                                "raw": data
                            }
                        }
                    except Exception as exc:
                        last_error = exc
                        if attempt == 2:
                            break
                        await asyncio.sleep(1.0)

        raise RuntimeError(f"Échec sur tous les modèles Gemini ({models_to_try}). Dernier log: {last_error}")
