from typing import Any, Dict, List
from core.providers.iresearch_provider import IResearchProvider
from core.providers.jina_provider import JinaProvider
from core.providers.tavily_provider import TavilyProvider
from core.providers.gemini_provider import GeminiProvider
from core.providers.searxng_provider import SearXNGProvider


class ResearchRouter:
    def __init__(self, providers: List[IResearchProvider]):
        self.providers = providers

    async def search(self, query: str, mode: str = "FAST", **kwargs: Any) -> Dict[str, Any]:
        if not self.providers:
            raise RuntimeError("Aucun fournisseur de recherche configuré.")

        # Sélection de providers selon le mode
        if mode == "FAST":
            # Jina + Tavily en priorité
            selected = [p for p in self.providers if isinstance(p, (JinaProvider, TavilyProvider))]
        elif mode == "RESEARCH":
            # Jina + Tavily + Gemini
            selected = [p for p in self.providers if isinstance(p, (JinaProvider, TavilyProvider, GeminiProvider))]
        elif mode == "FORENSIC":
            # SearXNG (local) en priorité
            selected = [p for p in self.providers if isinstance(p, SearXNGProvider)]
        else:
            selected = self.providers

        if not selected:
            selected = self.providers

        last_error = None
        for provider in selected:
            try:
                result = await provider.search(query, **kwargs)
                if result:
                    return result
            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(f"Échec de recherche sur tous les fournisseurs. Dernier log: {last_error}")
