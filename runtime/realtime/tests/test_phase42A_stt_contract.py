import asyncio
import json
import sys
import time
import numpy as np
from pathlib import Path

root_dir = Path(r"G:\AI\E-zzio")
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import bootstrap
from runtime.realtime.stt import MockSttProvider, SpeechBufferEngine

async def run_audit():
    start_time_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    mock_stt = MockSttProvider(canned_text="E-ZZIO V7 opérationnel.", latency_ms=10.0)
    engine = SpeechBufferEngine(stt_provider=mock_stt)
    
    checks = {}
    chunk = np.ones((512, 1), dtype=np.float32)
    
    await engine.process_vad_frame({"event": "SPEECH_STARTED", "audio": chunk})
    c1 = engine.metrics_audit["buffers_opened"] == 1
    checks["speech_started_opens_buffer"] = c1
    
    await engine.process_vad_frame({"event": "SPEECH_ONGOING", "audio": chunk})
    c2 = engine.metrics_audit["chunks_accumulated"] == 2
    checks["speech_ongoing_accumulates"] = c2
    
    silence_chunk = np.zeros((512, 1), dtype=np.float32)
    res3 = await engine.process_vad_frame({"event": "SPEECH_ENDED", "audio": silence_chunk})
    c3 = engine.metrics_audit["buffers_frozen"] == 1
    checks["speech_ended_freezes_buffer"] = c3
    
    checks["stt_result_received"] = (res3 is not None and res3.text == "E-ZZIO V7 opérationnel.")
    checks["mock_stt_called_once"] = (mock_stt.call_count == 1)
    
    mock_stt.fail_next = True
    await engine.process_vad_frame({"event": "SPEECH_STARTED", "audio": chunk})
    res_err = await engine.process_vad_frame({"event": "SPEECH_ENDED", "audio": chunk})
    checks["stt_failure_isolated"] = (res_err is None and engine.metrics_audit["errors_isolated"] == 1)
    
    await engine.process_vad_frame({"event": "SPEECH_STARTED", "audio": chunk})
    res_next_end = await engine.process_vad_frame({"event": "SPEECH_ENDED", "audio": chunk})
    checks["next_utterance_isolated"] = (res_next_end is not None and mock_stt.call_count == 3)

    failed = [k for k, v in checks.items() if not v]
    is_certified = len(failed) == 0

    report = {
        "component": "STT Contract & Buffer Engine",
        "phase": "4.2-A",
        "timestamp_utc": start_time_utc,
        "status": "CERTIFIED" if is_certified else "FAILED",
        "checks": checks,
        "metrics": {
            "audit_counters": engine.metrics_audit,
            "total_stt_calls": mock_stt.call_count
        },
        "evidence": {"failed_checks": failed},
        "score": 10 if is_certified else 0
    }

    report_file = root_dir / "runtime" / "realtime" / "tests" / "reports" / "phase42A_report.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not is_certified:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_audit())
