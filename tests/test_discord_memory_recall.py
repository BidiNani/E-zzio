import pytest
from core.memory.unified_gateway import UnifiedMemoryGateway
from core.router.intent_router import IntentRouter, IntentType


@pytest.mark.asyncio
async def test_cross_session_memory_search_and_recall(tmp_path):
    db_file = str(tmp_path / "test_discord_recall.db")
    gateway = UnifiedMemoryGateway(db_file)
    await gateway.init()

    # 1. Enregistrement dans deux sessions distinctes
    await gateway.record_message("sess_discord_user1", "user", "On configure l'architecture microkernel sur le port 8001")
    await gateway.record_message("sess_discord_user1", "assistant", "Architecture microkernel validée sur 8001.")
    await gateway.record_message("sess_discord_user2", "user", "Note : la clé API Tavily est injectée via secrets/.env")

    # 2. Recherche cross-session
    results = await gateway.search_memory("microkernel", limit=5)
    chat_hist = results.get("chat_history", [])

    assert len(chat_hist) >= 1
    assert any("8001" in m.get("content", "") for m in chat_hist)

    # 3. Test de classification d'intention pour le recall
    router = IntentRouter()
    classification = router.classify("Rappel de ce qu'on a fait précédemment concernant le microkernel")
    assert classification["intent"] == IntentType.MEMORY_QUERY
