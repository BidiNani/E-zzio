import pytest
from typing import Any, Dict
from core.providers.iresearch_provider import IResearchProvider
from core.decision_router import DecisionRouter, SearchMode

class MockProvider(IResearchProvider):
    def __init__(self, name: str, success: bool = True):
        self.name = name
        self.success = success

    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        if not self.success:
            raise ConnectionError(f"Mock error on {self.name}")
        return {"provider": self.name, "data": {"result": f"Result from {self.name}"}}

@pytest.mark.asyncio
async def test_research_mode_prioritizes_jina_over_tavily():
    # Instanciation intentionnellement inversée
    p_tavily = MockProvider("tavily")
    p_jina = MockProvider("jina")
    p_gemini = MockProvider("gemini")
    
    router = DecisionRouter(providers=[p_tavily, p_jina, p_gemini])
    
    # En mode RESEARCH, Jina DOIT répondre en premier
    res = await router.search("test query", mode=SearchMode.RESEARCH)
    assert res["provider"] == "jina"
    assert res["mode"] == "research"

@pytest.mark.asyncio
async def test_fast_mode_prioritizes_tavily_over_jina():
    p_jina = MockProvider("jina")
    p_tavily = MockProvider("tavily")
    
    router = DecisionRouter(providers=[p_jina, p_tavily])
    
    # En mode FAST, Tavily DOIT répondre en premier
    res = await router.search("test query", mode=SearchMode.FAST)
    assert res["provider"] == "tavily"
    assert res["mode"] == "fast"

@pytest.mark.asyncio
async def test_local_mode_calls_ollama():
    p_ollama = MockProvider("ollama")
    p_gemini = MockProvider("gemini")
    
    router = DecisionRouter(providers=[p_gemini, p_ollama])
    res = await router.search("test query", mode=SearchMode.LOCAL)
    assert res["provider"] == "ollama"
    assert res["mode"] == "local"
