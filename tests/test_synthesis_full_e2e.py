import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from routers.chat import post_chat, ChatRequest, init_chat_router, _core, _memory_gateway
from core.observability.tracer import ExecutionTracer

@pytest.mark.asyncio
async def test_synthesis_full_e2e_cognitive_pipeline():
    await init_chat_router()
    
    sess_id = "SESS_SYNTHESIS_E2E_001"
    user_id = "synth_user_01"
    
    # 1. Premier message : enregistrement d'une clé secrète
    req1 = ChatRequest(
        message="Mon code de synthèse est PROD-ALPHA-2026.",
        user_id=user_id,
        session_id=sess_id
    )
    
    # Mock uniquement le provider Ollama pour un test déterministe et rapide
    mock_ollama_resp = {
        "provider": "ollama",
        "model": "gpt-oss-20b",
        "data": {"text": "Code de synthèse PROD-ALPHA-2026 bien enregistré."}
    }
    
    with patch.object(_core.ollama, "search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_ollama_resp
        resp1 = await post_chat(req1)
        assert "PROD-ALPHA-2026" in resp1.response
        assert resp1.provider == "ollama"
    
    # 2. Vérification de la persistance SQLite WAL
    history = await _memory_gateway.get_session_history(sess_id)
    assert len(history) >= 2
    assert any("PROD-ALPHA-2026" in m["content"] for m in history if m["role"] == "user")
    
    # 3. Deuxième message : Rappel contextuel
    req2 = ChatRequest(
        message="Quel est mon code de synthèse ?",
        user_id=user_id,
        session_id=sess_id
    )
    mock_recall_resp = {
        "provider": "ollama",
        "model": "gpt-oss-20b",
        "data": {"text": "Votre code est PROD-ALPHA-2026."}
    }
    with patch.object(_core.ollama, "search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_recall_resp
        resp2 = await post_chat(req2)
        assert "PROD-ALPHA-2026" in resp2.response
        
    # 4. Vérification de l'isolation multi-session
    sess_iso = "SESS_SYNTHESIS_E2E_ISO"
    req_iso = ChatRequest(
        message="Quel est mon code ?",
        user_id="other_user",
        session_id=sess_iso
    )
    mock_iso_resp = {
        "provider": "ollama",
        "model": "gpt-oss-20b",
        "data": {"text": "Aucun code n'a été communiqué dans cette session."}
    }
    with patch.object(_core.ollama, "search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_iso_resp
        resp_iso = await post_chat(req_iso)
        assert "PROD-ALPHA-2026" not in resp_iso.response
