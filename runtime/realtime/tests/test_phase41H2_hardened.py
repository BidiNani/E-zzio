import asyncio
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(r"G:\AI\E-zzio")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.realtime.audio import AsyncAudioRecorder


MODEL = ROOT / "runtime" / "realtime" / "models" / "vad" / "silero_vad.onnx"
REPORTS = ROOT / "runtime" / "realtime" / "tests" / "reports"

REPORT = REPORTS / "phase41H2_report.json"
CONTRACT = REPORTS / "phase41H2_onnx_contract.json"


async def run_audit():

    started = time.perf_counter()

    REPORTS.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not MODEL.exists():
        raise AssertionError(
            f"Modèle absent : {MODEL}"
        )

    print("=" * 80)
    print(" E-ZZIO V7 — PHASE 4.1-H2 HARDENED VAD CERTIFICATION")
    print("=" * 80)
    print(f"[MODEL] {MODEL}")
    print(f"[MODEL] {MODEL.stat().st_size:,} bytes")

    recorder = AsyncAudioRecorder(
        vad_model_path=str(MODEL),
        sample_rate=16000,
        chunk_samples=512,
        queue_size=8,
        virtual_mode=True,
    )

    # ------------------------------------------------------------------
    # CONTRACT
    # ------------------------------------------------------------------

    contract = recorder.vad.contract()

    with open(
        CONTRACT,
        "w",
        encoding="utf-8",
    ) as fh:
        json.dump(
            contract,
            fh,
            indent=2,
        )

    print("[CONTRACT] ONNX contract validated")
    print(
        "[CONTRACT] Inputs:",
        list(contract["inputs"].keys()),
    )
    print(
        "[CONTRACT] Outputs:",
        list(contract["outputs"].keys()),
    )

    # ------------------------------------------------------------------
    # CHAOS
    # ------------------------------------------------------------------

    events = []
    frames = []
    inference_latencies = []
    queue_latencies = []

    speech_started_at = None
    speech_ended_at = None

    async def producer():

        await asyncio.sleep(0.05)

        t = np.arange(
            512,
            dtype=np.float32,
        ) / 16000.0

        # Voix synthétique non constante.
        speech = (
            0.35 * np.sin(
                2.0 * np.pi * 220.0 * t
            )
            + 0.20 * np.sin(
                2.0 * np.pi * 440.0 * t
            )
        ).astype(np.float32)

        speech = speech.reshape(
            -1,
            1,
        )

        silence = np.zeros(
            (512, 1),
            dtype=np.float32,
        )

        print("[CHAOS] Injection SPEECH x5")

        for _ in range(5):

            recorder.feed_virtual_chunk(
                speech,
                time.perf_counter(),
            )

            await asyncio.sleep(
                0.032
            )

        print("[CHAOS] Injection SILENCE x20")

        for _ in range(20):

            recorder.feed_virtual_chunk(
                silence,
                time.perf_counter(),
            )

            await asyncio.sleep(
                0.032
            )

        await asyncio.sleep(0.100)

        recorder.stop()

    async def consumer():

        nonlocal speech_started_at
        nonlocal speech_ended_at

        async for frame in recorder.listen_stream():

            frames.append(frame)

            event = frame["event"]

            events.append(event)

            metrics = frame["metrics"]

            inference_latencies.append(
                metrics["vad_inference_ms"]
            )

            queue_latencies.append(
                metrics[
                    "callback_to_dequeue_ms"
                ]
            )

            if event == "SPEECH_STARTED":
                speech_started_at = time.perf_counter()

            elif event == "SPEECH_ENDED":
                speech_ended_at = time.perf_counter()

    producer_task = asyncio.create_task(
        producer()
    )

    consumer_task = asyncio.create_task(
        consumer()
    )

    try:

        await asyncio.wait_for(
            producer_task,
            timeout=5.0,
        )

        await asyncio.wait_for(
            consumer_task,
            timeout=5.0,
        )

    finally:

        recorder.stop()

        if not producer_task.done():
            producer_task.cancel()

        if not consumer_task.done():
            consumer_task.cancel()

    # ------------------------------------------------------------------
    # FORENSIC ASSERTIONS
    # ------------------------------------------------------------------

    print("")
    print("[FORENSIC] Vérification événements")

    assert frames, (
        "FAIL: aucune frame VAD produite."
    )

    assert (
        "SPEECH_STARTED" in events
    ), (
        "FAIL: SPEECH_STARTED absent."
    )

    assert (
        "SPEECH_ENDED" in events
    ), (
        "FAIL: SPEECH_ENDED absent."
    )

    started_index = events.index(
        "SPEECH_STARTED"
    )

    ended_index = events.index(
        "SPEECH_ENDED"
    )

    assert ended_index > started_index, (
        "FAIL: ordre des événements invalide."
    )

    assert all(
        np.isfinite(x)
        for x in inference_latencies
    ), (
        "FAIL: latences VAD invalides."
    )

    assert all(
        x >= 0
        for x in queue_latencies
    ), (
        "FAIL: latence queue négative."
    )

    max_inference = max(
        inference_latencies
    )

    p95_inference = float(
        np.percentile(
            inference_latencies,
            95,
        )
    )

    max_queue = max(
        queue_latencies
    )

    p95_queue = float(
        np.percentile(
            queue_latencies,
            95,
        )
    )

    # SLA CPU réaliste.
    assert max_inference < 15.0, (
        f"FAIL: inference VAD "
        f"{max_inference:.3f} ms > 15 ms."
    )

    # Le pipeline ne doit pas accumuler de latence.
    assert max_queue < 50.0, (
        f"FAIL: queue latency "
        f"{max_queue:.3f} ms > 50 ms."
    )

    # Aucun overflow dans un test nominal.
    assert recorder.overflow_count == 0, (
        "FAIL: overflow détecté dans le test nominal."
    )

    # ------------------------------------------------------------------
    # SCORE
    # ------------------------------------------------------------------

    criteria = {
        "onnx_contract": True,
        "speech_started": (
            "SPEECH_STARTED" in events
        ),
        "speech_ended": (
            "SPEECH_ENDED" in events
        ),
        "event_order": (
            ended_index > started_index
        ),
        "finite_metrics": all(
            np.isfinite(x)
            for x in inference_latencies
        ),
        "inference_sla": (
            max_inference < 15.0
        ),
        "queue_sla": (
            max_queue < 50.0
        ),
        "no_nominal_overflow": (
            recorder.overflow_count == 0
        ),
        "pipeline_completed": True,
    }

    passed = sum(
        1
        for value in criteria.values()
        if value
    )

    total = len(criteria)

    score = (
        10.0 * passed / total
    )

    certified = (
        passed == total
        and score == 10.0
    )

    # ------------------------------------------------------------------
    # REPORT
    # ------------------------------------------------------------------

    report = {
        "component": (
            "Hardened Silero V5 VAD "
            "& Async Capture"
        ),
        "phase": "4.1-H2",
        "status": (
            "CERTIFIED"
            if certified
            else "FAILED"
        ),
        "certified": certified,
        "score": round(score, 2),
        "score_passed": passed,
        "score_total": total,
        "metrics": {
            "frames_processed": len(frames),
            "events": events,
            "silero_inference_max_ms": round(
                max_inference,
                4,
            ),
            "silero_inference_p95_ms": round(
                p95_inference,
                4,
            ),
            "queue_latency_max_ms": round(
                max_queue,
                4,
            ),
            "queue_latency_p95_ms": round(
                p95_queue,
                4,
            ),
            "queue_overflow_count": (
                recorder.overflow_count
            ),
            "callback_count": (
                recorder.callback_count
            ),
        },
        "criteria": criteria,
        "contract": contract,
        "timestamp_utc": (
            time.strftime(
                "%Y-%m-%dT%H:%M:%SZ",
                time.gmtime(),
            )
        ),
        "duration_ms": round(
            (
                time.perf_counter()
                - started
            ) * 1000.0,
            3,
        ),
    }

    with open(
        REPORT,
        "w",
        encoding="utf-8",
    ) as fh:

        json.dump(
            report,
            fh,
            indent=2,
        )

    # ------------------------------------------------------------------
    # OUTPUT
    # ------------------------------------------------------------------

    print("")
    print("=" * 80)
    print(" FORENSIC RESULT")
    print("=" * 80)

    print(
        f"Frames processed       : {len(frames)}"
    )

    print(
        f"Events                 : {events}"
    )

    print(
        f"Max Silero inference   : "
        f"{max_inference:.3f} ms"
    )

    print(
        f"P95 Silero inference   : "
        f"{p95_inference:.3f} ms"
    )

    print(
        f"Max queue latency      : "
        f"{max_queue:.3f} ms"
    )

    print(
        f"Queue overflow         : "
        f"{recorder.overflow_count}"
    )

    print(
        f"Criteria               : "
        f"{passed}/{total}"
    )

    print(
        f"SCORE                  : "
        f"{score:.2f}/10"
    )

    print(
        f"STATUS                 : "
        f"{'CERTIFIED' if certified else 'FAILED'}"
    )

    print(
        f"REPORT                 : {REPORT}"
    )

    print(
        f"CONTRACT               : {CONTRACT}"
    )

    print("=" * 80)

    if not certified:
        raise AssertionError(
            "PHASE 4.1-H2 NOT CERTIFIED."
        )


if __name__ == "__main__":
    asyncio.run(
        run_audit()
    )