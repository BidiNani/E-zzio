import os
import aiohttp
from typing import Dict, Any
from dotenv import load_dotenv
from pathlib import Path

ENV_PATH = Path(__file__).parent.parent.parent / "secrets" / ".env"
load_dotenv(dotenv_path=ENV_PATH)

class HybridCognitiveRouter:
    """Routeur intelligent basculant entre le calcul local (Ollama) et le Cloud (Gemini Pro)."""
    
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

    async def _call_gemini_pro(self, prompt: str, system_prompt: str) -> str:
        if not self.gemini_api_key:
            return "⚠️ [Erreur] Clé Gemini Pro non trouvée. Le mode Cloud est désactivé."

        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": f"{system_prompt}\n\nUser: {prompt}"}]}]
        }
        url = f"{self.gemini_endpoint}?key={self.gemini_api_key}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["candidates"][0]["content"]["parts"][0]["text"]
                    else:
                        error_text = await resp.text()
                        raise Exception(f"Gemini API Error {resp.status}: {error_text}")
        except Exception as e:
            raise Exception(f"Erreur de communication Cloud: {str(e)}")

    async def _call_local_cpu(self, prompt: str) -> str:
        return f"💻 [Local CPU Mode] Requête traitée en local (Simulé en attendant Ollama) : {prompt}"

    async def generate_response(self, prompt: str, system_prompt: str, force_local: bool = False) -> str:
        """Détermine dynamiquement le meilleur modèle à utiliser."""
        # Logique de routage : Si la requête est complexe, on utilise Gemini Pro.
        needs_cloud = len(prompt) > 200 or "analyse" in prompt.lower() or "code" in prompt.lower()
        
        if force_local or not needs_cloud or not self.gemini_api_key:
            try:
                return await self._call_local_cpu(prompt)
            except Exception:
                pass

        return await self._call_gemini_pro(prompt, system_prompt)
