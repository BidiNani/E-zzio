import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from routers.chat import post_chat, ChatRequest, ChatResponse, init_chat_router, _core, _memory_gateway
from core.voice.voice_gateway import VoiceGateway
from core.decision_router import DecisionRouter, SearchMode
from core.memory.unified_gateway import UnifiedMemoryGateway

@pytest.mark.asyncio
async def test_chat_contract_explicit_types_and_fields():
    await init_chat_router()
    req = ChatRequest(
        message="Message de test contrat",
        user_id="contract_user",
        session_id="SESS_CONTRACT_001"
    )
    
    with patch.object(_core.ollama, "search", new_callable=AsyncMock) as mock_s:
        mock_s.return_value = {
            "provider": "ollama",
            "model": "gpt-oss-20b",
            "data": {"text": "Réponse conforme au contrat."}
        }
        resp = await post_chat(req)
        
        # Validation stricte du contrat ChatResponse
        assert isinstance(resp, ChatResponse)
        assert isinstance(resp.response, str) and len(resp.response) > 0
        assert isinstance(resp.intent, str) and resp.intent == "local_chat"
        assert isinstance(resp.provider, str) and resp.provider == "ollama"
        assert isinstance(resp.mode, str)
        assert isinstance(resp.session_id, str) and resp.session_id == "SESS_CONTRACT_001"
        assert isinstance(resp.data, dict)

@pytest.mark.asyncio
async def test_voice_contract_explicit_fields():
    gw = VoiceGateway()
    mock_core = MagicMock()
    mock_core.think = AsyncMock(return_value={"response": "Réponse vocale", "provider": "ollama"})
    
    res = await gw.process_voice_interaction(
        audio_data=bytes(16000),
        core=mock_core,
        session_id="SESS_VOICE_CONTRACT"
    )
    
    assert "transcription" in res and isinstance(res["transcription"], str)
    assert "response_text" in res and isinstance(res["response_text"], str)
    assert "audio_out" in res and isinstance(res["audio_out"], bytes)
    assert "status" in res and res["status"] == "success"
    assert "session_id" in res and res["session_id"] == "SESS_VOICE_CONTRACT"

@pytest.mark.asyncio
async def test_failure_recovery_database_and_restoration(tmp_path):
    db_path = str(tmp_path / "recovery_test.db")
    gw = UnifiedMemoryGateway(db_path=db_path)
    await gw.init()
    
    # 1. Écriture nominale
    await gw.record_message("SESS_REC", "user", "Message avant panne")
    h1 = await gw.get_session_history("SESS_REC")
    assert len(h1) == 1
    
    # 2. Simulation de reprise
    await gw.init()
    await gw.record_message("SESS_REC", "assistant", "Message après reprise")
    h2 = await gw.get_session_history("SESS_REC")
    assert len(h2) == 2
    assert h2[0]["content"] == "Message avant panne"
    assert h2[1]["content"] == "Message après reprise"
