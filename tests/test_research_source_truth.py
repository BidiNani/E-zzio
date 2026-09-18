import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.decision_router import DecisionRouter, SearchMode
from core.providers.iresearch_provider import IResearchProvider


class MockProvider(IResearchProvider):
    def __init__(self, name: str, return_value=None, side_effect=None):
        self.name = name
        self.return_value = return_value
        self.side_effect = side_effect

    async def search(self, query: str, **kwargs):
        if self.side_effect:
            if isinstance(self.side_effect, Exception):
                raise self.side_effect
            return await self.side_effect(query, **kwargs)
        return self.return_value

@pytest.mark.asyncio
async def test_research_preserves_authentic_source_provenance():
    # Fournisseur retournant des sources réelles avec URL authentique
    authentic_data = {
        "results": [
            {"title": "E-ZZIO Whitepaper", "url": "https://ezzio.org/paper.pdf", "content": "Architecture souveraine."},
            {"title": "E-ZZIO Docs", "url": "https://docs.ezzio.org", "content": "Guide de référence."}
        ],
        "total": 2
    }
    p_searxng = MockProvider("searxng", {"provider": "searxng", "data": authentic_data})

    router = DecisionRouter([p_searxng])
    res = await router.search("architecture E-ZZIO", mode=SearchMode.FORENSIC)

    assert res["provider"] == "searxng"
    results = res["data"]["results"]
    assert len(results) == 2
    assert results[0]["url"] == "https://ezzio.org/paper.pdf"
    assert results[0]["title"] == "E-ZZIO Whitepaper"
    assert results[1]["url"] == "https://docs.ezzio.org"

@pytest.mark.asyncio
async def test_research_deterministic_fallback_on_timeout_and_error():
    # Jina lève un Timeout, Tavily prend le relais proprement
    p_jina = MockProvider("jina", side_effect=TimeoutError("Timeout réseau"))
    p_tavily = MockProvider("tavily", {
        "provider": "tavily",
        "data": {"results": [{"title": "Tavily Result", "url": "https://tavily.com/1", "content": "Contenu Tavily"}]}
    })

    router = DecisionRouter([p_jina, p_tavily])
    res = await router.search("requête fallback", mode=SearchMode.FAST)

    assert res["provider"] == "tavily"
    assert res["data"]["results"][0]["url"] == "https://tavily.com/1"

@pytest.mark.asyncio
async def test_research_fail_closed_when_all_providers_fail():
    p1 = MockProvider("tavily", side_effect=RuntimeError("Clé API invalide"))
    p2 = MockProvider("jina", side_effect=RuntimeError("Quota dépassé"))

    router = DecisionRouter([p1, p2])
    with pytest.raises(RuntimeError) as exc_info:
        await router.search("requête", mode=SearchMode.FAST)

    err_msg = str(exc_info.value)
    assert "Échec de recherche (fast) sur tous les fournisseurs qualifiés" in err_msg
    assert "tavily" in err_msg
    assert "jina" in err_msg
