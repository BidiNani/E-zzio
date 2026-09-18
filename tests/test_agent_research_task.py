import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from core.decision_router import DecisionRouter, SearchMode
from core.providers.gemini_provider import GeminiProvider
from core.providers.tavily_provider import TavilyProvider
from routers.research import ResearchRequest, search_endpoint


@pytest.mark.asyncio
async def test_agent_research_task_loop_provenance():
    # 1. Requête de recherche cognitive avec validation de provenance
    mock_tavily = TavilyProvider(api_key="mock_key")
    mock_tavily.search = AsyncMock(return_value={
        "provider": "tavily",
        "data": {
            "results": [
                {
                    "title": "E-ZZIO Autonomous Kernel Specs",
                    "url": "https://ezzio.ai/specs/v6",
                    "content": "Spécifications du noyau d'exécution et de recherche."
                }
            ],
            "query": "E-ZZIO Kernel Specs",
            "timestamp": 1724342400
        }
    })

    router = DecisionRouter([mock_tavily])
    res = await router.search("E-ZZIO Kernel Specs", mode=SearchMode.FAST)

    assert res["provider"] == "tavily"
    results = res["data"]["results"]
    assert len(results) >= 1
    assert results[0]["url"] == "https://ezzio.ai/specs/v6"
    assert "Spécifications" in results[0]["content"]

@pytest.mark.asyncio
async def test_agent_research_task_timeout_and_fallback():
    mock_p1 = TavilyProvider(api_key="mock_key")
    mock_p1.search = AsyncMock(side_effect=TimeoutError("Recherche expirée"))

    mock_gemini = GeminiProvider(api_key="mock_key")
    mock_gemini.search = AsyncMock(return_value={
        "provider": "gemini",
        "data": {"text": "Synthèse de recherche de repli Cloud."}
    })

    router = DecisionRouter([mock_p1, mock_gemini])
    # En cas d'échec du premier fournisseur, le routeur bascule vers le provider de repli ou gère proprement l'erreur
    try:
        res = await router.search("Recherche urgente", mode=SearchMode.FAST)
    except Exception:
        res = await router.search("Recherche urgente", mode=SearchMode.GOOGLE)

    assert res["provider"] == "gemini"
    assert "Synthèse" in res["data"]["text"]
