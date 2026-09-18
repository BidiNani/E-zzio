import os
import re

import pytest

from core.observability.tracer import ExecutionTracer


@pytest.mark.asyncio
async def test_execution_tracer_lifecycle(tmp_path):
    db_file = str(tmp_path / "test_tracer.db")
    tracer = ExecutionTracer(db_path=db_file)
    await tracer.init()

    await tracer.log_trace(
        provider="ollama",
        mode="local_chat",
        latency_ms=123.45,
        status="success",
        session_id="sess_obs_001",
        request_id="req_obs_001",
        model="gpt-oss-20b"
    )

    traces = await tracer.get_recent_traces(limit=5)
    assert len(traces) == 1
    t = traces[0]
    assert t["provider"] == "ollama"
    assert t["mode"] == "local_chat"
    assert t["latency_ms"] == 123.45
    assert t["status"] == "success"
    assert t["session_id"] == "sess_obs_001"
    assert t["request_id"] == "req_obs_001"
    assert t["model"] == "gpt-oss-20b"

@pytest.mark.asyncio
async def test_observability_no_secret_leakage(tmp_path):
    db_file = str(tmp_path / "test_tracer_sec.db")
    tracer = ExecutionTracer(db_path=db_file)
    await tracer.init()

    # Enregistrement d'une trace
    await tracer.log_trace(
        provider="gemini",
        mode="google",
        latency_ms=450.0,
        status="success",
        session_id="sess_sec_001",
        request_id="req_sec_001",
        model="gemini-3.7-flash"
    )

    traces = await tracer.get_recent_traces(limit=10)
    for row in traces:
        for k, v in row.items():
            if v is not None:
                # Vérifier qu'aucun token / clé API brute n'apparaît
                assert not re.search(r"AIzaSy[A-Za-z0-9_-]{33}", str(v)), "Clé Google API trouvée dans la trace !"
                assert not re.search(r"tvly-[A-Za-z0-9]{32}", str(v)), "Clé Tavily trouvée dans la trace !"
                assert not re.search(r"jina_[A-Za-z0-9]{32}", str(v)), "Clé Jina trouvée dans la trace !"
