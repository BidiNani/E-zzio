import asyncio
import json
import os
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(r"G:/AI/E-zzio").resolve()
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from interfaces.api.server import app

from core.memory.unified_gateway import UnifiedMemoryGateway
from scripts.backup_ezzio import backup_ezzio
from scripts.watchdog_ezzio import EzzioWatchdog
from tools.fs_tools import observe_filesystem


async def run_benchmarks():
    print("=== EXECUTING E-ZZIO PRODUCTION BENCHMARKS ===")
    metrics = {}
    proc = psutil.Process(os.getpid())

    # 1. API Readiness
    client = TestClient(app)
    t0 = time.perf_counter()
    r = client.get("/api/v1/health/readiness")
    t1 = time.perf_counter()
    metrics["readiness_ms"] = round((t1 - t0) * 1000, 2)
    assert r.status_code == 200

    # 2. Chat Latency
    t0 = time.perf_counter()
    r_chat = client.post("/api/v1/chat", json={
        "message": "Test benchmark latency",
        "session_id": "BENCH_SESS_01"
    }, headers={"X-API-Key": "ezzio_secret_key_local_dev"})
    t1 = time.perf_counter()
    metrics["chat_ms"] = round((t1 - t0) * 1000, 2)
    assert r_chat.status_code == 200

    # 3. Memory Retrieval / Insertion
    db_p = str(ROOT / "runtime" / "test_tmp" / "bench_mem.db")
    os.makedirs(os.path.dirname(db_p), exist_ok=True)
    gw = UnifiedMemoryGateway(db_path=db_p)
    await gw.init()

    t0 = time.perf_counter()
    await gw.record_message("BENCH_SESS_01", "user", "Benchmark Fact Data", {})
    t1 = time.perf_counter()
    metrics["memory_insert_ms"] = round((t1 - t0) * 1000, 2)

    t0 = time.perf_counter()
    hist = await gw.get_session_history("BENCH_SESS_01")
    t1 = time.perf_counter()
    metrics["memory_retrieval_ms"] = round((t1 - t0) * 1000, 2)
    assert len(hist) == 1

    # 4. Filesystem Scan
    t0 = time.perf_counter()
    obs = observe_filesystem("core")
    t1 = time.perf_counter()
    metrics["filesystem_scan_ms"] = round((t1 - t0) * 1000, 2)
    metrics["core_python_files_count"] = len([f for f in obs["files"].keys() if f.endswith(".py")])

    # 5. Task Engine Execution
    t0 = time.perf_counter()
    r_task = client.post("/api/v1/tasks/", json={
        "objective": "Inspecte G:/AI/E-zzio et denombre les fichiers python dans core/",
        "session_id": "BENCH_SESS_01"
    })
    t_id = r_task.json()["task_id"]
    r_run = client.post(f"/api/v1/tasks/{t_id}/run")
    t1 = time.perf_counter()
    metrics["task_execution_ms"] = round((t1 - t0) * 1000, 2)
    assert r_run.status_code == 200

    # 6. Watchdog Check Latency
    wd = EzzioWatchdog()
    t0 = time.perf_counter()
    chk = wd.run_once()
    t1 = time.perf_counter()
    metrics["watchdog_check_ms"] = round((t1 - t0) * 1000, 2)

    # 7. Backup Execution Latency & Size
    t0 = time.perf_counter()
    bk = backup_ezzio()
    t1 = time.perf_counter()
    metrics["backup_time_ms"] = round((t1 - t0) * 1000, 2)
    metrics["backup_size_bytes"] = bk["size_bytes"]

    # 8. Memory & CPU footprint
    metrics["process_ram_mb"] = round(proc.memory_info().rss / (1024 * 1024), 2)
    metrics["cpu_percent"] = proc.cpu_percent(interval=0.1)

    out_file = ROOT / "_forensic" / "final_integration" / "BASELINE_METRICS.json"
    out_file.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print("Benchmark completed:\n", json.dumps(metrics, indent=2))
    return metrics

if __name__ == "__main__":
    asyncio.run(run_benchmarks())
