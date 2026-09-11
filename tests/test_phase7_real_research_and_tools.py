import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from tools.fs_tools import observe_filesystem, read_file, list_directory
from core.decision_router import DecisionRouter, SearchMode
from core.providers.tavily_provider import TavilyProvider
from core.providers.jina_provider import JinaProvider
from core.providers.searxng_provider import SearxngProvider
from core.providers.gemini_provider import GeminiProvider

def test_phase7_tools_execution_read_and_observe(tmp_path):
    target = tmp_path / "p7_env"
    target.mkdir()
    sample = target / "manifest.json"
    sample.write_text('{"project": "E-ZZIO", "phase": 7}', encoding="utf-8")
    
    # 1. Observation
    obs = observe_filesystem(str(target))
    assert obs["status"] == "SUCCESS"
    assert "manifest.json" in obs["files"]
    
    # 2. List
    lst = list_directory(str(target))
    assert "manifest.json" in lst
    
    # 3. Read
    content = read_file(str(sample))
    assert "E-ZZIO" in content

@pytest.mark.asyncio
async def test_phase7_research_multi_provider_cascade():
    # Simulation du comportement de fallback entre 2 providers réels
    p_searxng = SearxngProvider()
    p_gemini = GeminiProvider(api_key="mock_key")
    
    router = DecisionRouter([p_searxng, p_gemini])
    
    with patch.object(p_searxng, "search", new_callable=AsyncMock) as mock_s, \
         patch.object(p_gemini, "search", new_callable=AsyncMock) as mock_g:
        
        # Cas 1 : Premier provider échoue (ex: réseau indisponible)
        mock_s.side_effect = RuntimeError("SearxNG connection failed")
        
        # Cas 2 : Deuxième provider réussit avec provenance réelle
        mock_g.return_value = {
            "provider": "gemini",
            "data": {
                "results": [
                    {"title": "E-ZZIO Security Matrix", "url": "https://ezzio.ai/security", "content": "Règles constitutionnelles strictes"}
                ],
                "text": "Réponse garantie par le fallback Gemini."
            }
        }
        
        res = await router.search("Sécurité constitutionnelle", mode=SearchMode.GOOGLE)
        assert res["provider"] == "gemini"
        assert len(res["data"]["results"]) == 1
        assert res["data"]["results"][0]["url"] == "https://ezzio.ai/security"
