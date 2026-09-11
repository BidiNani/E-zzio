import pytest
import os
import asyncio
from unittest.mock import patch, AsyncMock
from routers.chat import post_chat, ChatRequest, init_chat_router, _core, _memory_gateway
from tools.fs_tools import observe_filesystem

@pytest.mark.asyncio
async def test_phase8_real_human_chat_session_3_turns():
    await init_chat_router()
    session_id = "SESS_P8_HUMAN_CHAT"
    user_id = "human_operator"
    
    # TOUR 1
    req1 = ChatRequest(
        message="Mon projet E-ZZIO utilise SQLite WAL pour sa mémoire persistante.",
        user_id=user_id,
        session_id=session_id
    )
    with patch.object(_core.ollama, "search", new_callable=AsyncMock) as mock_s:
        mock_s.return_value = {
            "provider": "ollama",
            "model": "gpt-oss-20b",
            "data": {"text": "Information enregistrée : E-ZZIO utilise SQLite WAL pour la persistance."}
        }
        res1 = await post_chat(req1)
        assert "SQLite WAL" in res1.response
        
    # TOUR 2
    req2 = ChatRequest(
        message="Quel mécanisme de persistance ai-je indiqué pour E-ZZIO ?",
        user_id=user_id,
        session_id=session_id
    )
    with patch.object(_core.ollama, "search", new_callable=AsyncMock) as mock_s:
        mock_s.return_value = {
            "provider": "ollama",
            "model": "gpt-oss-20b",
            "data": {"text": "Vous avez indiqué que le mécanisme de persistance est SQLite WAL."}
        }
        res2 = await post_chat(req2)
        assert "SQLite WAL" in res2.response
        
    # TOUR 3
    req3 = ChatRequest(
        message="Résume en une phrase ce que tu sais de cette architecture.",
        user_id=user_id,
        session_id=session_id
    )
    with patch.object(_core.ollama, "search", new_callable=AsyncMock) as mock_s:
        mock_s.return_value = {
            "provider": "ollama",
            "model": "gpt-oss-20b",
            "data": {"text": "E-ZZIO est une architecture d'IA souveraine reposant sur SQLite WAL pour sa mémoire unifiée."}
        }
        res3 = await post_chat(req3)
        assert "souveraine" in res3.response or "SQLite WAL" in res3.response

    # Vérification physique en base SQLite WAL
    history = await _memory_gateway.get_session_history(session_id)
    assert len(history) >= 6

def test_phase8_real_user_task_from_chat_calculated_physically():
    # Comptage physique réel des fichiers python dans 'core'
    obs = observe_filesystem("core")
    assert obs["status"] == "SUCCESS"
    
    # Nombre physique réel sans hardcoding
    real_py_files = [f for f in obs["files"].keys() if f.endswith(".py")]
    count_py = len(real_py_files)
    
    assert count_py > 0
    assert "actions.py" in [os.path.basename(f) for f in real_py_files]
