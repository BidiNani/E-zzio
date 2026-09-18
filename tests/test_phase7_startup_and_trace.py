import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest

from core.observability.tracer import ExecutionTracer


def test_phase7_one_command_start_and_stop():
    root = Path(__file__).resolve().parent.parent
    start_script = root / "scripts" / "start_ezzio.py"
    stop_script = root / "scripts" / "stop_ezzio.py"

    # 1. Démarrage
    p_start = subprocess.run([sys.executable, str(start_script)], capture_output=True, text=True)
    assert p_start.returncode == 0
    assert "E-ZZIO READY" in p_start.stdout

    # 2. Arrêt
    p_stop = subprocess.run([sys.executable, str(stop_script)], capture_output=True, text=True)
    assert p_stop.returncode == 0
    assert "ARRET DU SYSTEME" in p_stop.stdout

@pytest.mark.asyncio
async def test_phase7_task_trace_forensic_reconstruction(tmp_path):
    db_file = str(tmp_path / "forensic_trace_p7.db")
    tracer = ExecutionTracer(db_path=db_file)
    await tracer.init()

    t_id = "TASK_P7_TRACE_999"
    r_id = "REQ_P7_TRACE_001"

    # Enregistrement de trace
    await tracer.log_trace(
        provider="ollama",
        mode="task_execution",
        latency_ms=95.4,
        status="SUCCESS",
        session_id="SESS_P7",
        request_id=r_id,
        model="gpt-oss-20b"
    )

    # Reconstitution complète 1:1
    traces = await tracer.get_recent_traces(limit=10)
    found = [t for t in traces if t["request_id"] == r_id]
    assert len(found) == 1
    assert found[0]["status"] == "SUCCESS"
    assert found[0]["latency_ms"] == 95.4
