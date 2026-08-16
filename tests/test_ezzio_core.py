import pytest
from typing import Any, Dict
from runtime.core.ezzio_core import EzzioCore
from core.memory.unified_gateway import UnifiedMemoryGateway
from core.router.intent_router import IntentRouter
from core.decision_router import DecisionRouter, SearchMode
from core.providers.iresearch_provider import IResearchProvider

class MockTestProvider(IResearchProvider):
    def __init__(self, name: str):
        self.name = name

    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "data": {
                "text": f"Réponse mockée par {self.name}",
                "results": [{"title": "Lien Mock", "url": "https://test.local"}]
            }
        }

@pytest.mark.asyncio
async def test_ezzio_core_autonomous_pipeline(tmp_path):
    db_file = str(tmp_path / "test_core_memory.db")
    memory = UnifiedMemoryGateway(db_file)
    await memory.init()

    providers = [
        MockTestProvider("ollama"),
        MockTestProvider("tavily"),
        MockTestProvider("jina"),
        MockTestProvider("gemini")
    ]
    decision_router = DecisionRouter(providers=providers)
    core = EzzioCore(memory_gateway=memory, decision_router=decision_router)

    # 1. Test Chat Local
    res_chat = await core.think(user_id="u1", message="Bonjour, comment vas-tu ?")
    assert res_chat["intent"] == "local_chat"
    assert res_chat["provider"] == "ollama"
    assert "ollama" in res_chat["response"]

    # 2. Test Recherche Web
    res_search = await core.think(user_id="u1", message="Cherche les dernières nouveautés IA")
    assert res_search["intent"] == "web_search"
    assert res_search["mode"] == "web_search"

    # 3. Test Raisonnement Lourd
    res_deep = await core.think(user_id="u1", message="Analyse cette architecture complexe et propose un refactor")
    assert res_deep["intent"] == "deep_reasoning"
    assert res_deep["provider"] == "gemini"

    # 4. Test Mémoire / Rappel
    res_mem = await core.think(user_id="u1", message="Rappel de notre historique")
    assert res_mem["intent"] == "memory_query"
    assert res_mem["mode"] == "memory_recall"

    # Vérification que l'historique contient bien les échanges
    history = await memory.get_session_history("sess_u1", limit=10)
    assert len(history) == 8  # 4 questions + 4 réponses
