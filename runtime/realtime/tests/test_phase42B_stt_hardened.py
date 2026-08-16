import asyncio
import hashlib
import json
import sys
import time
import numpy as np
from pathlib import Path

ROOT = Path(r"G:\AI\E-zzio")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bootstrap

from runtime.realtime.stt import (
    MockSttProvider,
    SpeechBufferEngine,
)


REPORT = (
    ROOT
    / "runtime"
    / "realtime"
    / "tests"
    / "reports"
    / "phase42B_report.json"
)


def utc_now():
    return time.strftime(
        "%Y-%m-%dT%H:%M:%SZ",
        time.gmtime()
    )


async def run_audit():

    started = time.perf_counter()

    checks = {}
    evidence = {}
    errors = []

    # ------------------------------------------------------------------
    # PROVIDER
    # ------------------------------------------------------------------

    provider = MockSttProvider(
        canned_text="E-ZZIO V7 Phase 4.2-B OK.",
        latency_ms=10.0
    )

    engine = SpeechBufferEngine(
        stt_provider=provider
    )

    # ------------------------------------------------------------------
    # TEST DATA
    # ------------------------------------------------------------------

    speech_chunk = np.ones(
        (512, 1),
        dtype=np.float32
    )

    ongoing_chunk = np.full(
        (512, 1),
        0.5,
        dtype=np.float32
    )

    end_chunk = np.zeros(
        (512, 1),
        dtype=np.float32
    )

    # ------------------------------------------------------------------
    # 1 — EMPTY / IRRELEVANT EVENTS MUST NOT OPEN BUFFER
    # ------------------------------------------------------------------

    await engine.process_vad_frame({
        "event": "SILENCE",
        "audio": end_chunk
    })

    checks["silence_does_not_open_buffer"] = (
        engine.metrics_audit["buffers_opened"] == 0
    )

    # ------------------------------------------------------------------
    # 2 — SPEECH_STARTED
    # ------------------------------------------------------------------

    await engine.process_vad_frame({
        "event": "SPEECH_STARTED",
        "audio": speech_chunk
    })

    checks["speech_started_opens_buffer"] = (
        engine.metrics_audit["buffers_opened"] == 1
    )

    checks["first_chunk_accumulated"] = (
        engine.metrics_audit["chunks_accumulated"] == 1
    )

    # ------------------------------------------------------------------
    # 3 — ONGOING ACCUMULATION
    # ------------------------------------------------------------------

    await engine.process_vad_frame({
        "event": "SPEECH_ONGOING",
        "audio": ongoing_chunk
    })

    checks["ongoing_accumulates"] = (
        engine.metrics_audit["chunks_accumulated"] == 2
    )

    # ------------------------------------------------------------------
    # 4 — END FREEZES SNAPSHOT
    # ------------------------------------------------------------------

    result = await engine.process_vad_frame({
        "event": "SPEECH_ENDED",
        "audio": end_chunk
    })

    checks["ended_freezes_buffer"] = (
        engine.metrics_audit["buffers_frozen"] == 1
    )

    checks["stt_result_received"] = (
        result is not None
        and result.text == "E-ZZIO V7 Phase 4.2-B OK."
    )

    checks["provider_called_once"] = (
        provider.call_count == 1
    )

    # ------------------------------------------------------------------
    # 5 — EMPTY END MUST NOT CALL STT
    # ------------------------------------------------------------------

    provider_before = provider.call_count

    empty_engine = SpeechBufferEngine(
        stt_provider=provider
    )

    empty_result = await empty_engine.process_vad_frame({
        "event": "SPEECH_ENDED",
        "audio": end_chunk
    })

    checks["orphan_speech_ended_ignored"] = (
        empty_result is None
        and provider.call_count == provider_before
    )

    # ------------------------------------------------------------------
    # 6 — MULTI-UTTERANCE ISOLATION
    # ------------------------------------------------------------------

    await engine.process_vad_frame({
        "event": "SPEECH_STARTED",
        "audio": speech_chunk
    })

    await engine.process_vad_frame({
        "event": "SPEECH_ONGOING",
        "audio": ongoing_chunk
    })

    result_2 = await engine.process_vad_frame({
        "event": "SPEECH_ENDED",
        "audio": end_chunk
    })

    checks["second_utterance_independent"] = (
        result_2 is not None
        and provider.call_count == 2
        and engine.metrics_audit["buffers_opened"] == 2
        and engine.metrics_audit["buffers_frozen"] == 2
    )

    # ------------------------------------------------------------------
    # 7 — FAILURE ISOLATION + RECOVERY
    # ------------------------------------------------------------------

    provider.fail_next = True

    await engine.process_vad_frame({
        "event": "SPEECH_STARTED",
        "audio": speech_chunk
    })

    failed_result = await engine.process_vad_frame({
        "event": "SPEECH_ENDED",
        "audio": end_chunk
    })

    checks["stt_failure_returns_none"] = (
        failed_result is None
    )

    checks["failure_counter_incremented"] = (
        engine.metrics_audit["errors_isolated"] == 1
    )

    # ------------------------------------------------------------------
    # 8 — POST FAILURE RECOVERY
    # ------------------------------------------------------------------

    recovered_result = await engine.process_vad_frame({
        "event": "SPEECH_STARTED",
        "audio": speech_chunk
    })

    recovered_result = await engine.process_vad_frame({
        "event": "SPEECH_ENDED",
        "audio": end_chunk
    })

    checks["post_failure_recovery"] = (
        recovered_result is not None
        and provider.call_count == 4
    )

    # ------------------------------------------------------------------
    # 9 — INPUT IMMUTABILITY
    # ------------------------------------------------------------------

    original = np.array(
        speech_chunk,
        copy=True
    )

    immutability_engine = SpeechBufferEngine(
        stt_provider=provider
    )

    await immutability_engine.process_vad_frame({
        "event": "SPEECH_STARTED",
        "audio": speech_chunk
    })

    input_unchanged = np.array_equal(
        speech_chunk,
        original
    )

    checks["input_audio_untouched"] = (
        input_unchanged
    )

    # ------------------------------------------------------------------
    # 10 — LATENCY EVIDENCE
    # ------------------------------------------------------------------

    checks["stt_latency_recorded"] = (
        result is not None
        and "stt_exec_ms" in result.latencies
        and result.latencies["stt_exec_ms"] >= 0
    )

    # ------------------------------------------------------------------
    # METRICS
    # ------------------------------------------------------------------

    elapsed_ms = (
        time.perf_counter() - started
    ) * 1000.0

    evidence["provider_calls"] = provider.call_count
    evidence["audit_counters"] = engine.metrics_audit
    evidence["last_result"] = (
        recovered_result.text
        if recovered_result is not None
        else None
    )
    evidence["input_audio_untouched"] = input_unchanged

    failed = [
        name
        for name, value in checks.items()
        if not value
    ]

    certified = (
        len(failed) == 0
    )

    report = {
        "component":
            "STT Hardened Integration",

        "phase":
            "4.2-B",

        "status":
            "CERTIFIED"
            if certified
            else "FAILED",

        "score":
            10
            if certified
            else 0,

        "timestamp_utc":
            utc_now(),

        "checks":
            checks,

        "metrics": {
            "total_runtime_ms":
                elapsed_ms,

            "provider_calls":
                provider.call_count,

            "audit_counters":
                engine.metrics_audit
        },

        "evidence":
            evidence,

        "errors":
            errors,

        "failed_checks":
            failed
    }

    REPORT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    REPORT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False
        )
    )

    if not certified:
        return 1

    return 0


if __name__ == "__main__":

    try:
        code = asyncio.run(
            run_audit()
        )

    except BaseException as exc:

        print("")
        print(
            "FATAL PHASE 4.2-B ERROR:",
            repr(exc)
        )

        raise

    sys.exit(code)
