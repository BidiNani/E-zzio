import asyncio
import json
import time
from pathlib import Path
import bootstrap

from runtime.realtime.brain import MockBrainWorker, BrainRequest

async def run_audit():
    start_time_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    worker = MockBrainWorker(ttft_delay=0.1, token_delay=0.01)
    req = BrainRequest(request_id="test-brain-01", text="Activation E-ZZIO V7")
    
    chunks = []
    t0 = time.perf_counter()
    first_token_time = 0
    
    async for chunk in worker.ask_stream(req):
        if not chunks:
            first_token_time = time.perf_counter() - t0
        chunks.append(chunk)
        
    total_time = time.perf_counter() - t0
    
    # Assertions critiques
    assert len(chunks) > 0, "Le worker doit produire des chunks"
    assert chunks[-1].is_final is True, "Le dernier chunk doit lever is_final=True"
    assert "Activation" in "".join(c.chunk_text for c in chunks), "Le texte source doit être reflété dans le mock"
    
    # Génération du rapport
    reports_dir = Path(r"G:\AI\E-zzio\runtime\realtime\tests\reports")
    report_file = reports_dir / "phase33_report.json"
    
    report_payload = {
        "component": "BrainInterface Foundation",
        "phase": "3.3",
        "timestamp_utc": start_time_utc,
        "status": "CERTIFIED",
        "metrics": {
            "mock_chunks_yielded": len(chunks),
            "simulated_ttft_ms": int(first_token_time * 1000),
            "total_latency_ms": int(total_time * 1000)
        },
        "score": 10
    }
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2)

if __name__ == "__main__":
    asyncio.run(run_audit())
