"""
E-ZZIO V7.24.2 — Ollama Provider Adapter
Pont entre l'Intelligence Router et le Governor local. Respecte le contrat BaseProvider.
"""
import time
from typing import Optional, Dict, Any
from providers.base_provider import BaseProvider
from providers.provider_response import ProviderResponse

class OllamaProvider(BaseProvider):
    def __init__(self):
        self.host = "http://127.0.0.1:11434"

    def capabilities(self) -> list:
        return ["reasoning", "coding", "fast_chat", "vision", "local_privacy"]

    def health(self) -> Dict[str, Any]:
        # En production, interrogera l'API /api/tags d'Ollama [non vérifié]
        return {
            "provider": "ollama",
            "healthy": True,
            "status": "OPERATIONAL",
            "capabilities": self.capabilities()
        }

    async def generate(self, prompt: str, model: Optional[str] = "qwen3:8b", image_bytes: Optional[bytes] = None, capability: str = "default") -> ProviderResponse:
        import aiohttp
        import asyncio

        start_time = time.perf_counter()
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        # NOTE : La logique réelle de Swap intelligent via le Governor interviendra ici
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.host}/api/generate", json=payload, timeout=120) as resp:
                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                    if resp.status == 200:
                        data = await resp.json()
                        return ProviderResponse(
                            ok=True,
                            provider="ollama",
                            model=model,
                            content=data.get("response", ""),
                            latency_ms=round(elapsed_ms, 2)
                        )
                    else:
                        return ProviderResponse(ok=False, provider="ollama", model=model, error=f"Ollama HTTP {resp.status}")
        except Exception as e:
            return ProviderResponse(ok=False, provider="ollama", model=model, error=f"Ollama Exception: {str(e)}")
