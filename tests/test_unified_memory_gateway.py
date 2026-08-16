import pytest
from core.memory.unified_gateway import UnifiedMemoryGateway

@pytest.mark.asyncio
async def test_record_and_retrieve_session_history(tmp_path):
    db_file = str(tmp_path / "test_memory.db")
    gateway = UnifiedMemoryGateway(db_file)
    await gateway.init()

    session_id = "test_sess_01"
    await gateway.record_message(session_id, "user", "Première question")
    await gateway.record_message(session_id, "assistant", "Première réponse")

    history = await gateway.get_session_history(session_id, limit=5)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Première question"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Première réponse"

@pytest.mark.asyncio
async def test_search_memory_cross_query(tmp_path):
    db_file = str(tmp_path / "test_memory.db")
    gateway = UnifiedMemoryGateway(db_file)
    await gateway.init()

    session_id = "test_sess_02"
    await gateway.record_message(session_id, "user", "Comment configurer SQLite WAL ?")

    # Stockage d'une preuve d'investigation
    await gateway.evidence_store.store(
        query="SQLite WAL",
        provider="tavily",
        mode="fast",
        data={"results": [{"title": "Doc WAL", "url": "https://sqlite.org"}]}
    )

    search_res = await gateway.search_memory("WAL")
    assert len(search_res["chat_history"]) >= 1
    assert len(search_res["evidences"]) >= 1
    assert "SQLite" in search_res["chat_history"][0]["content"]
