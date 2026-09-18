from enum import Enum
from typing import Any

from core.providers.iresearch_provider import IResearchProvider


class SearchMode(Enum):
    FAST = "fast"
    RESEARCH = "research"
    FORENSIC = "forensic"
    GOOGLE = "google"
    LOCAL = "local"


class DecisionRouter:
    MODE_PRIORITIES = {
        SearchMode.FAST: ["tavily", "jina"],
        SearchMode.RESEARCH: ["jina", "tavily", "gemini"],
        SearchMode.GOOGLE: ["gemini"],
        SearchMode.LOCAL: ["ollama"],
        SearchMode.FORENSIC: ["searxng", "jina"],
    }

    def __init__(self, providers: list[IResearchProvider]):
        self.providers = providers
        self._provider_map: dict[str, IResearchProvider] = {getattr(p, "name", ""): p for p in providers if hasattr(p, "name")}

    def _select_providers(self, mode: SearchMode) -> list[IResearchProvider]:
        priority_names = self.MODE_PRIORITIES.get(mode, [])
        ordered = [self._provider_map[name] for name in priority_names if name in self._provider_map]
        return ordered if ordered else self.providers

    async def search(self, query: str, mode: SearchMode = SearchMode.FAST, **kwargs: Any) -> dict[str, Any]:
        if not self.providers:
            raise RuntimeError("Aucun fournisseur de recherche configuré.")

        selected = self._select_providers(mode)
        errors: list[str] = []

        for provider in selected:
            provider_name = getattr(provider, "name", "unknown")
            try:
                result = await provider.search(query, **kwargs)
                if result:
                    return {"mode": mode.value, "provider": result.get("provider", provider_name), "data": result.get("data", {})}
            except Exception as e:
                # Capture explicite du type et de la représentation technique complète
                err_detail = f"[{provider_name}] {type(e).__name__}: {e!r}"
                errors.append(err_detail)
                continue

        error_summary = " | ".join(errors) if errors else "Aucune exception levée mais aucun résultat produit."
        raise RuntimeError(f"Échec de recherche ({mode.value}) sur tous les fournisseurs qualifiés. Journal: {error_summary}")
