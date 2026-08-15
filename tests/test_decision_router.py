import pytest
from typing import Any, Dict
from core.providers.iresearch_provider import IResearchProvider
from core.decision_router import DecisionRouter, SearchMode

class DummyProviderSuccess(IResearchProvider):
    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        return {"provider": "dummy_ok", "data": [f"Result for {query}"]}

class DummyProviderFail(IResearchProvider):
    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        raise ConnectionError("Service injoignable")

@pytest.mark.asyncio
async def test_decision_router_fast_mode():
    p_ok = DummyProviderSuccess()
    router = DecisionRouter(providers=[p_ok])
    res = await router.search("test", mode=SearchMode.FAST)
    assert res is not None
    assert res["mode"] == "fast"

@pytest.mark.asyncio
async def test_decision_router_research_mode():
    p_ok = DummyProviderSuccess()
    router = DecisionRouter(providers=[p_ok])
    res = await router.search("test", mode=SearchMode.RESEARCH)
    assert res is not None
    assert res["mode"] == "research"

@pytest.mark.asyncio
async def test_decision_router_forensic_mode():
    p_ok = DummyProviderSuccess()
    router = DecisionRouter(providers=[p_ok])
    res = await router.search("test", mode=SearchMode.FORENSIC)
    assert res is not None
    assert res["mode"] == "forensic"

@pytest.mark.asyncio
async def test_decision_router_google_mode():
    p_ok = DummyProviderSuccess()
    router = DecisionRouter(providers=[p_ok])
    res = await router.search("test", mode=SearchMode.GOOGLE)
    assert res is not None
    assert res["mode"] == "google"
