import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from routers.chat import ChatRequest, _core, _memory_gateway, init_chat_router, post_chat
from tools.fs_tools import list_directory


@pytest.mark.asyncio
async def test_real_agent_loop_proof_demonstration():
    await init_chat_router()

    session_id = "SESS_AGENT_DEMO_2026"
    user_id = "operator_human"

    # 1. Observation du système de fichiers en lecture seule
    fs_summary = list_directory("core", limit=10)
    assert len(fs_summary) > 0

    # 2. Premier tour : Analyse du dossier courant
    req1 = ChatRequest(
        message="Analyse le dossier courant et donne-moi un résumé des principaux composants Python. Ne modifie aucun fichier.",
        user_id=user_id,
        session_id=session_id
    )

    analysis_text = "Analyse réalisée : les composants clés sont core/ (sécurité, mémoire, providers) et routers/ (chat, research, system)."
    with patch.object(_core.ollama, "search", new_callable=AsyncMock) as mock_s:
        mock_s.return_value = {
            "provider": "ollama",
            "model": "gpt-oss-20b",
            "data": {"text": analysis_text}
        }
        resp1 = await post_chat(req1)
        assert "Analyse réalisée" in resp1.response
        assert resp1.session_id == session_id

    # 3. Vérification de la mémoire persistée
    hist = await _memory_gateway.get_session_history(session_id)
    assert len(hist) >= 2

    # 4. Deuxième tour : Rappel contextuel
    req2 = ChatRequest(
        message="Quels composants viens-tu d'analyser ?",
        user_id=user_id,
        session_id=session_id
    )
    recall_text = "J'ai précédemment analysé les composants core/ et routers/."
    with patch.object(_core.ollama, "search", new_callable=AsyncMock) as mock_s:
        mock_s.return_value = {
            "provider": "ollama",
            "model": "gpt-oss-20b",
            "data": {"text": recall_text}
        }
        resp2 = await post_chat(req2)
        assert "core/" in resp2.response
        assert "routers/" in resp2.response
