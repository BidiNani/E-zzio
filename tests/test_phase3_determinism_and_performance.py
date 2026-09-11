import pytest
import asyncio
import time
import statistics
from unittest.mock import AsyncMock, patch
from core.memory.unified_gateway import UnifiedMemoryGateway
from core.decision_router import DecisionRouter, SearchMode
from core.observability.tracer import ExecutionTracer
from routers.chat import post_chat, ChatRequest, init_chat_router, _core

@pytest.mark.asyncio
async def test_determinism_multi_run_invariants():
    await init_chat_router()
    
    # 5 itérations identiques consécutives
    for iteration in range(5):
        sess_id = f"DETERMINISM_SESS_{iteration}"
        req = ChatRequest(
            message=f"Ping déterminisme {iteration}",
            user_id="det_user",
            session_id=sess_id
        )
        
        with patch.object(_core.ollama, "search", new_callable=AsyncMock) as mock_s:
            mock_s.return_value = {
                "provider": "ollama",
                "model": "gpt-oss-20b",
                "data": {"text": f"Pong {iteration}"}
            }
            resp = await post_chat(req)
            
            assert resp.response == f"Pong {iteration}"
            assert resp.provider == "ollama"
            assert resp.intent == "local_chat"
            assert resp.session_id == sess_id

@pytest.mark.asyncio
async def test_performance_latency_baseline_metrics(tmp_path):
    db_path = str(tmp_path / "perf_test.db")
    gw = UnifiedMemoryGateway(db_path=db_path)
    await gw.init()
    
    tracer = ExecutionTracer(db_path=db_path)
    await tracer.init()
    
    write_latencies = []
    read_latencies = []
    fts_latencies = []
    trace_latencies = []
    
    # 20 itérations de mesure
    for i in range(20):
        # Mesure écriture
        t0 = time.perf_counter()
        await gw.record_message("PERF_SESS", "user", f"Mesure de latence index {i}")
        write_latencies.append((time.perf_counter() - t0) * 1000)
        
        # Mesure lecture
        t0 = time.perf_counter()
        await gw.get_session_history("PERF_SESS")
        read_latencies.append((time.perf_counter() - t0) * 1000)
        
        # Mesure FTS5
        t0 = time.perf_counter()
        await gw.search_memory("latence")
        fts_latencies.append((time.perf_counter() - t0) * 1000)
        
        # Mesure Tracer
        t0 = time.perf_counter()
        await tracer.log_trace("ollama", "local", 10.0, "success", session_id="PERF_SESS")
        trace_latencies.append((time.perf_counter() - t0) * 1000)
        
    print(f"\n[PERF BASELINE] Write (ms): mean={statistics.mean(write_latencies):.2f}, p95={statistics.quantiles(write_latencies, n=20)[18]:.2f}")
    print(f"[PERF BASELINE] Read (ms): mean={statistics.mean(read_latencies):.2f}, p95={statistics.quantiles(read_latencies, n=20)[18]:.2f}")
    print(f"[PERF BASELINE] FTS5 (ms): mean={statistics.mean(fts_latencies):.2f}, p95={statistics.quantiles(fts_latencies, n=20)[18]:.2f}")
    print(f"[PERF BASELINE] Trace (ms): mean={statistics.mean(trace_latencies):.2f}, p95={statistics.quantiles(trace_latencies, n=20)[18]:.2f}")
    
    assert statistics.mean(write_latencies) < 100.0, "Latence moyenne d'écriture WAL SQLite anormale"
    assert statistics.mean(read_latencies) < 50.0, "Latence moyenne de lecture anormale"
