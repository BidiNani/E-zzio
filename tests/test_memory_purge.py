import pytest

from core.memory.unified_gateway import UnifiedMemoryGateway


@pytest.mark.asyncio
async def test_memory_purge_operations(tmp_path):
    db_file = str(tmp_path / "test_purge.db")
    gateway = UnifiedMemoryGateway(db_file)
    await gateway.init()

    # 1. Insertion de données de test
    await gateway.record_message("disc_user_123", "user", "Message confidentiel secret_token_abc")
    await gateway.record_message("disc_user_123", "assistant", "Réponse avec secret_token_abc")
    await gateway.record_message("disc_user_456", "user", "Autre message sans rapport")

    # 2. Test clear_session
    deleted_session = await gateway.clear_session("disc_user_456")
    assert deleted_session == 1
    rem_456 = await gateway.get_session_history("disc_user_456")
    assert len(rem_456) == 0

    # 3. Test purge_by_keyword
    purge_res = await gateway.purge_by_keyword("secret_token_abc")
    assert purge_res["messages_deleted"] == 2

    # Vérification que la mémoire est vide pour ce mot clé
    search_res = await gateway.search_memory("secret_token_abc")
    assert len(search_res["chat_history"]) == 0
