from unittest.mock import AsyncMock

import pytest

from runtime.core.ezzio_core import EzzioCore


@pytest.mark.asyncio
async def test_think_unbound_local_error_fix():
    """
    Test garantissant que data_dict est bien instancié même
    si le decision_router est désactivé ou échoue (fallback).
    """
    mock_memory = AsyncMock()
    core = EzzioCore(memory_gateway=mock_memory)

    # On désactive volontairement le decision_router pour forcer le chemin alternatif
    core.decision_router = None

    # On mock le fallback
    core.ollama = AsyncMock()
    core.ollama.search.return_value = {"data": {"text": "Mocked fallback response"}, "provider": "ollama"}

    # L'appel ne doit plus crasher sur UnboundLocalError
    result = await core.think(user_id="test_n8n", message="Hello webhook", session_id="sess_1")

    assert result["status"] == "success"
    assert result["response"] == "Mocked fallback response"
    assert "model_used" in result
