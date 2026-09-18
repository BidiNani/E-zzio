import asyncio

import pytest

from core.observability.tracer import ExecutionTracer


@pytest.mark.asyncio
async def test_trace_reconstruction_complete_chain(tmp_path):
    db_path = str(tmp_path / "forensic_trace.db")
    tracer = ExecutionTracer(db_path=db_path)
    await tracer.init()

    # 1. Enregistrement d'un cycle complet
    sess_id = "SESS_FORENSIC_TRACE_001"
    req_id = "REQ_CHAIN_999"

    await tracer.log_trace(
        provider="ollama",
        mode="local_chat",
        latency_ms=85.2,
        status="success",
        session_id=sess_id,
        request_id=req_id,
        model="gpt-oss-20b"
    )

    # 2. Reconstruction de la preuve à partir de SQLite
    traces = await tracer.get_recent_traces(limit=10)
    matching = [t for t in traces if t["request_id"] == req_id]

    assert len(matching) == 1
    t = matching[0]
    assert t["session_id"] == sess_id
    assert t["provider"] == "ollama"
    assert t["model"] == "gpt-oss-20b"
    assert t["status"] == "success"
    assert t["latency_ms"] == 85.2
