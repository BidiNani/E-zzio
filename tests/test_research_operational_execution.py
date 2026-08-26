import pytest
import os
from core.decision_router import DecisionRouter, SearchMode
from core.providers.tavily_provider import TavilyProvider
from core.providers.jina_provider import JinaProvider
from core.providers.searxng_provider import SearxngProvider
from core.providers.gemini_provider import GeminiProvider

@pytest.mark.asyncio
async def test_research_operational_router_instantiation_and_modes():
    p_tavily = TavilyProvider()
    p_jina = JinaProvider()
    p_searxng = SearxngProvider()
    
    router = DecisionRouter([p_tavily, p_jina, p_searxng])
    assert router is not None
    assert SearchMode.FAST.value == "fast"
    assert SearchMode.RESEARCH.value == "research"
    assert SearchMode.FORENSIC.value == "forensic"

@pytest.mark.asyncio
async def test_research_operational_provenance_contract():
    # Fournisseur avec structure de réponse réelle
    from unittest.mock import AsyncMock
    mock_tavily = TavilyProvider(api_key="mock_key")
    mock_tavily.search = AsyncMock(return_value={
        "provider": "tavily",
        "data": {
            "results": [
                {
                    "title": "E-ZZIO Autonomous Systems",
                    "url": "https://ezzio.ai/docs",
                    "content": "Documentation technique du socle souverain."
                }
            ],
            "query": "architecture souveraine",
            "timestamp": 1724342400
        }
    })
    
    router = DecisionRouter([mock_tavily])
    res = await router.search("architecture souveraine", mode=SearchMode.FAST)
    
    assert res["provider"] == "tavily"
    assert "data" in res
    assert "results" in res["data"]
    item = res["data"]["results"][0]
    assert item["title"] == "E-ZZIO Autonomous Systems"
    assert item["url"] == "https://ezzio.ai/docs"
    assert "Documentation" in item["content"]
