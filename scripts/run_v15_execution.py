import asyncio
import os
import sys
import json
import time
import hashlib
import psutil
from pathlib import Path

ROOT = Path(r"G:/AI/E-zzio").resolve()
sys.path.insert(0, str(ROOT))

CERT_DIR = ROOT / "_forensic" / "final_integration"
os.makedirs(CERT_DIR, exist_ok=True)

from tools.fs_tools import observe_filesystem
from core.memory.unified_gateway import UnifiedMemoryGateway
from core.evidence_store import EvidenceStore
from fastapi.testclient import TestClient
from interfaces.api.server import app
from scripts.backup_ezzio import backup_ezzio, verify_backup
from scripts.status_production import get_production_status
from scripts.watchdog_ezzio import EzzioWatchdog

async def run_v15_suite():
    print("=== EXECUTING V15 COMPREHENSIVE PRODUCTION BENCHMARK & SOAK ===")
    proc = psutil.Process(os.getpid())
    
    # Baseline capture
    baseline = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "version": "15.0.0",
        "snapshots": {
            "MASTER_KNOWLEDGE": hashlib.sha256((ROOT / "_forensic/knowledge/MASTER_KNOWLEDGE.json").read_bytes()).hexdigest(),
            "FILE_HASHES": hashlib.sha256((ROOT / "_forensic/knowledge/FILE_HASHES.json").read_bytes()).hexdigest(),
            "drift_detector": hashlib.sha256((ROOT / "core/knowledge/drift_detector.py").read_bytes()).hexdigest()
        }
    }
    (CERT_DIR / "V15_BASELINE.json").write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    
    # 1. API Performance
    client = TestClient(app)
    t0 = time.perf_counter()
    r_ready = client.get("/api/v1/health/readiness")
    t1 = time.perf_counter()
    readiness_latency_ms = round((t1 - t0) * 1000, 2)
    assert r_ready.status_code == 200

    # 2. Soak / Stability test (5 cycles of chat, task, memory)
    soak_cycles = 5
    cycle_latencies = []
    
    mem_db = str(ROOT / "runtime" / "test_tmp" / "v15_soak_mem.db")
    os.makedirs(os.path.dirname(mem_db), exist_ok=True)
    gw = UnifiedMemoryGateway(db_path=mem_db)
    await gw.init()
    
    for i in range(soak_cycles):
        c_t0 = time.perf_counter()
        # Chat
        r_chat = client.post("/api/v1/chat", json={
            "message": f"Soak message cycle {i}",
            "session_id": f"SOAK_SESS_{i}"
        }, headers={"X-API-Key": "ezzio_secret_key_local_dev"})
        assert r_chat.status_code == 200
        
        # Memory
        await gw.record_message(f"SOAK_SESS_{i}", "user", f"Fact {i}", {})
        h = await gw.get_session_history(f"SOAK_SESS_{i}")
        assert len(h) == 1
        
        c_t1 = time.perf_counter()
        cycle_latencies.append(round((c_t1 - c_t0) * 1000, 2))
        
    avg_cycle_ms = round(sum(cycle_latencies) / len(cycle_latencies), 2)
    
    # 3. Memory & Resource Footprint
    mem_info = proc.memory_info()
    ram_mb = round(mem_info.rss / (1024 * 1024), 2)
    
    # 4. Status Check
    prod_status = get_production_status()
    
    # 5. Backup test
    bk = backup_ezzio()
    assert verify_backup(str(ROOT / "runtime" / "backups" / f"manifest_{bk['timestamp']}.json")) is True
    
    # 6. Results compilation
    results = {
        "status": "SUCCESS",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "version": "15.0.0",
        "metrics": {
            "readiness_latency_ms": readiness_latency_ms,
            "soak_cycles_completed": soak_cycles,
            "avg_soak_cycle_ms": avg_cycle_ms,
            "ram_footprint_mb": ram_mb,
            "backup_size_bytes": bk["size_bytes"]
        },
        "components_state": prod_status["components"]
    }
    
    (CERT_DIR / "V15_RESULTS.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("V15 Execution successfully completed and recorded.")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(run_v15_suite())
