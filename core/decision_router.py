from typing import Any, Dict, List, Optional
from enum import Enum
from core.providers.iresearch_provider import IResearchProvider

class SearchMode(Enum):
    FAST = "fast"
    RESEARCH = "research"
    FORENSIC = "forensic"
    GOOGLE = "google"
    LOCAL = "local"

class DecisionRouter:
    # Matrice de priorité stricte et déterministe par mode
    MODE_PRIORITIES = {
        SearchMode.FAST: ["tavily", "jina"],
        SearchMode.RESEARCH: ["jina", "tavily", "gemini"],
        SearchMode.GOOGLE: ["gemini"],
        SearchMode.LOCAL: ["ollama"],
        SearchMode.FORENSIC: ["searxng", "jina"],
    }

    def __init__(self, providers: List[IResearchProvider]):
        self.providers = providers
        # Indexation par le nom unique du provider
        self._provider_map: Dict[str, IResearchProvider] = {
            getattr(p, "name", ""): p for p in providers if hasattr(p, "name")
        }

    def _select_providers(self, mode: SearchMode) -> List[IResearchProvider]:
        """Sélectionne et ordonne les providers selon la priorité stricte du mode."""
        priority_names = self.MODE_PRIORITIES.get(mode, [])
        ordered = [self._provider_map[name] for name in priority_names if name in self._provider_map]
        return ordered if ordered else self.providers

    async def search(self, query: str, mode: SearchMode = SearchMode.FAST, **kwargs: Any) -> Dict[str, Any]:
        if not self.providers:
            raise RuntimeError("Aucun fournisseur de recherche configuré.")

        selected = self._select_providers(mode)
        last_error = None

        for provider in selected:
            try:
                result = await provider.search(query, **kwargs)
                if result:
                    return {
                        "mode": mode.value,
                        "provider": result.get("provider", getattr(provider, "name", "unknown")),
                        "data": result.get("data", {})
                    }
            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(f"Échec de recherche ({mode.value}) sur tous les fournisseurs qualifiés. Dernier log: {last_error}")
