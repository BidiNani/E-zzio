import pytest
from typing import Any, Dict
from core.providers.iresearch_provider import IResearchProvider
from core.research_router import ResearchRouter
from core.providers.jina_provider import JinaProvider
from core.providers.tavily_provider import TavilyProvider
from core.providers.gemini_provider import GeminiProvider

class DummyProviderSuccess(IResearchProvider):
    name = "dummy_ok"
    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        return {"provider": "dummy_ok", "results": [f"Result for {query}"]}

class DummyProviderFail(IResearchProvider):
    name = "dummy_fail"
    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        raise ConnectionError("Service injoignable")

@pytest.mark.asyncio
async def test_research_router_fallback_flow():
    p_fail = DummyProviderFail()
    p_ok = DummyProviderSuccess()

    router = ResearchRouter(providers=[p_fail, p_ok])
    res = await router.search("test sovereign query")

    assert res is not None
    assert res["provider"] == "dummy_ok"
    assert "Result for test sovereign query" in res["results"]

@pytest.mark.asyncio
async def test_research_router_no_providers():
    router = ResearchRouter(providers=[])
    with pytest.raises(RuntimeError, match="Aucun fournisseur de recherche configuré."):
        await router.search("test")

@pytest.mark.asyncio
async def test_jina_provider_structure():
    provider = JinaProvider()
    assert provider.base_url == "https://s.jina.ai"
    assert provider.name == "jina"

@pytest.mark.asyncio
async def test_tavily_provider_structure():
    provider = TavilyProvider(api_key="test")
    assert provider.base_url == "https://api.tavily.com/search"
    assert provider.name == "tavily"

@pytest.mark.asyncio
async def test_gemini_provider_structure():
    provider = GeminiProvider(api_key="test")
    assert provider.name == "gemini"
    assert "generativelanguage" in provider.base_url
    assert "gemini" in provider.model
