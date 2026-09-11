import pytest
from core.memory.unified_gateway import UnifiedMemoryGateway


@pytest.mark.asyncio
async def test_fts5_memory_search_and_triggers(tmp_path):
    db_file = str(tmp_path / "test_fts5.db")
    gateway = UnifiedMemoryGateway(db_file)
    await gateway.init()

    # 1. Insertion
    await gateway.record_message("s1", "user", "L'optimisation des microkernels via IPC synchrone est prioritaire.")
    await gateway.record_message("s1", "assistant", "Reçu, microkernel configuré.")
    await gateway.record_message("s2", "user", "Autre sujet sur SQLite WAL.")

    # 2. Recherche FTS5
    results = await gateway.search_memory("microkernels", limit=5)
    chat_hist = results.get("chat_history", [])
    assert len(chat_hist) >= 1
    assert "microkernels" in chat_hist[0]["content"]

    # 3. Purge et vérification de la suppression dans FTS5
    await gateway.purge_by_keyword("microkernels")
    after_purge = await gateway.search_memory("microkernels", limit=5)
    assert len(after_purge["chat_history"]) == 0
