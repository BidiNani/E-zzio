import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from core.memory.unified_gateway import UnifiedMemoryGateway
from routers.chat import post_chat, ChatRequest, init_chat_router, _core, _memory_gateway

@pytest.mark.asyncio
async def test_unified_memory_high_concurrency_writes_and_reads(tmp_path):
    db_path = str(tmp_path / "high_concurrency.db")
    gw = UnifiedMemoryGateway(db_path=db_path)
    await gw.init()
    
    num_sessions = 10
    messages_per_session = 5
    
    # 1. Écritures concurrentes massives
    async def session_worker(sess_idx):
        sess_name = f"HIGH_CONC_SESS_{sess_idx}"
        for m_idx in range(messages_per_session):
            await gw.record_message(
                session_id=sess_name,
                role="user" if m_idx % 2 == 0 else "assistant",
                content=f"SecretPayload_Sess{sess_idx}_Msg{m_idx}",
                metadata={"session_idx": sess_idx, "msg_idx": m_idx}
            )
            # Lecture intermédiaire concurrente
            hist = await gw.get_session_history(sess_name)
            assert len(hist) > 0
            
    workers = [session_worker(i) for i in range(num_sessions)]
    await asyncio.gather(*workers)
    
    # 2. Vérification d'intégrité et de non-pollution inter-sessions
    for i in range(num_sessions):
        sess_name = f"HIGH_CONC_SESS_{i}"
        hist = await gw.get_session_history(sess_name)
        assert len(hist) == messages_per_session
        
        # Vérification qu'aucun message d'une autre session n'est présent
        for m in hist:
            assert f"Sess{i}_" in m["content"]
            for other_i in range(num_sessions):
                if other_i != i:
                    assert f"Sess{other_i}_" not in m["content"]

    # 3. Vérification de l'index FTS5
    search_res = await gw.search_memory("SecretPayload_Sess3_Msg2")
    assert len(search_res["chat_history"]) >= 1
    assert "SecretPayload_Sess3_Msg2" in search_res["chat_history"][0]["content"]

@pytest.mark.asyncio
async def test_concurrent_core_requests_isolation():
    await init_chat_router()
    
    num_concurrent_requests = 10
    
    async def dynamic_search(query=None, prompt=None, **kwargs):
        text_in = query or prompt or ""
        tokens = [w for w in text_in.split() if w.startswith("TOK-")]
        tok = tokens[0] if tokens else "TOK-UNKNOWN"
        return {
            "provider": "ollama",
            "model": "gpt-oss-20b",
            "data": {"text": f"Confirmation code {tok}"}
        }
        
    with patch.object(_core.ollama, "search", side_effect=dynamic_search):
        async def request_task(req_id_idx):
            sess_id = f"CONCURRENT_CORE_SESS_{req_id_idx}"
            tok_code = f"TOK-{req_id_idx:04d}"
            req = ChatRequest(
                message=f"Mon code unique est {tok_code}",
                user_id=f"user_{req_id_idx}",
                session_id=sess_id
            )
            
            resp = await post_chat(req)
            assert tok_code in resp.response
            assert resp.session_id == sess_id
            
            # Vérification de l'historique dans la session isolée
            hist = await _memory_gateway.get_session_history(sess_id)
            assert len(hist) >= 2
            assert any(tok_code in m["content"] for m in hist)
            
        tasks = [request_task(i) for i in range(num_concurrent_requests)]
        await asyncio.gather(*tasks)
