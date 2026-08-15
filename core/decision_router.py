from typing import Any, Dict, List, Optional
from enum import Enum
from core.providers.iresearch_provider import IResearchProvider

class SearchMode(Enum):
    FAST = "fast"
    RESEARCH = "research"
    FORENSIC = "forensic"
    GOOGLE = "google"

class DecisionRouter:
    def __init__(self, providers: List[IResearchProvider]):
        self.providers = providers

    def _select_providers(self, mode: SearchMode) -> List[IResearchProvider]:
        """Sélectionne les providers selon le mode"""
        from core.providers.jina_provider import JinaProvider
        from core.providers.tavily_provider import TavilyProvider
        from core.providers.gemini_provider import GeminiProvider
        from core.providers.searxng_provider import SearXNGProvider

        if mode == SearchMode.FAST:
            # Jina + Tavily en priorité
            return [p for p in self.providers if isinstance(p, (JinaProvider, TavilyProvider))]
        elif mode == SearchMode.RESEARCH:
            # Jina + Tavily + Gemini
            return [p for p in self.providers if isinstance(p, (JinaProvider, TavilyProvider, GeminiProvider))]
        elif mode == SearchMode.FORENSIC:
            # SearXNG (local) en priorité
            return [p for p in self.providers if isinstance(p, SearXNGProvider)]
        elif mode == SearchMode.GOOGLE:
            # Gemini uniquement
            return [p for p in self.providers if isinstance(p, GeminiProvider)]
        else:
            return self.providers

    async def search(self, query: str, mode: SearchMode = SearchMode.FAST, **kwargs: Any) -> Dict[str, Any]:
        if not self.providers:
            raise RuntimeError("Aucun fournisseur de recherche configuré.")
        
        selected = self._select_providers(mode)
        
        if not selected:
            selected = self.providers
        
        last_error = None
        for provider in selected:
            try:
                result = await provider.search(query, **kwargs)
                if result:
                    return {"mode": mode.value, "provider": result["provider"], "data": result["data"]}
            except Exception as e:
                last_error = e
                continue
        
        raise RuntimeError(f"Échec de recherche sur tous les fournisseurs. Dernier log: {last_error}")
