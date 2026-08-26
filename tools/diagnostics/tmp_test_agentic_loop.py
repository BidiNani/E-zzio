import pytest
from unittest.mock import AsyncMock
from runtime.core.ezzio_core import EzzioCore


@pytest.mark.asyncio
async def test_agent_tool_invocation(tmp_path):
    # Setup
    mem = AsyncMock()
    mem.get_session_history = AsyncMock(return_value=[])
    router = AsyncMock()

    core = EzzioCore(memory_gateway=mem, decision_router=router)

    # Simuler une réponse du LLM contenant un appel d'outil
    router.search.return_value = {"data": {"text": '<tool>{"tool": "get_system_metrics", "args": {}}</tool>'}}

    # Exécution : le noyau devrait appeler get_system_metrics, puis boucler
    # On mocke le second appel du router pour retourner une réponse finale
    router.search.side_effect = [
        {"data": {"text": '<tool>{"tool": "get_system_metrics", "args": {}}</tool>'}},
        {"data": {"text": "L'utilisation CPU est de 25%."}},
    ]

    result = await core.think(user_id="test", message="Stats?")
    assert "25%" in result["response"]
