import pytest
import asyncio
from core.observability.tracer import ExecutionTracer

@pytest.mark.asyncio
async def test_task_forensic_trace_chain_reconstruction(tmp_path):
    db_path = str(tmp_path / "task_trace.db")
    tracer = ExecutionTracer(db_path=db_path)
    await tracer.init()
    
    t_id = "TASK_TRACE_001"
    s_id = "SESS_OBS_001"
    r_id = "REQ_CHAIN_100"
    
    # 1. Enregistrement d'un cycle de tâche complet
    await tracer.log_trace(
        provider="ollama",
        mode="task_execution",
        latency_ms=120.5,
        status="COMPLETED",
        session_id=s_id,
        request_id=r_id,
        model="gpt-oss-20b"
    )
    
    # 2. Reconstruction de la trace
    recent = await tracer.get_recent_traces(limit=5)
    matching = [t for t in recent if t["request_id"] == r_id]
    
    assert len(matching) == 1
    tr = matching[0]
    assert tr["session_id"] == s_id
    assert tr["mode"] == "task_execution"
    assert tr["status"] == "COMPLETED"
    assert tr["latency_ms"] == 120.5
