import sys
import asyncio
import logging
import time
import tempfile
from pathlib import Path

sys.path.insert(0, r'G:\AI\E-zzio')

violations = []

class StrictLoggingHandler(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.WARNING:
            violations.append(f"[LOGGING::{record.levelname}] {record.name}: {record.getMessage()}")

logging.getLogger().addHandler(StrictLoggingHandler())

try:
    from loguru import logger
    def loguru_sink(message):
        rec = message.record
        if rec["level"].no >= 30:
            violations.append(f"[LOGURU::{rec['level'].name}] {rec['name']}: {rec['message']}")
    logger.add(loguru_sink, level="WARNING")
except ImportError:
    pass

from runtime.realtime.pipecat.router import EzzioRealtimeRouter

class FakeTTS:
    def __init__(self):
        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        self.tmp_file.write(b'\x00' * 3200)
        self.tmp_file.close()

    async def synthesize(self, text):
        return {"ok": True, "audio_path": self.tmp_file.name, "duration": 0.1}

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineWorker
from pipecat.workers.runner import WorkerRunner
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import (
    Frame,
    StartFrame,
    TextFrame,
    OutputAudioRawFrame,
    InterruptionFrame,
    EndFrame
)

from runtime.realtime.pipecat.adapter import (
    EzzioRouterProcessor,
    EzzioTTSProcessor
)

class IntermediateRouterMetricsCollector(FrameProcessor):
    """Capte les TextFrames émis par le Routeur avant qu'ils ne soient consommés par le TTS."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.injection_time = None
        self.first_chunk_time_ms = None
        self.chunk_timestamps = []
        self.chunks_content = []
        self.start_frame_seen = False
        self.end_frame_seen = False
        self.interruption_seen = False
        self.audio_frames_seen = 0

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        now = time.perf_counter()
        
        if isinstance(frame, StartFrame):
            self.start_frame_seen = True
        elif isinstance(frame, EndFrame):
            self.end_frame_seen = True
        elif isinstance(frame, InterruptionFrame):
            self.interruption_seen = True
        elif isinstance(frame, TextFrame):
            if self.injection_time and not self.first_chunk_time_ms:
                self.first_chunk_time_ms = round((now - self.injection_time) * 1000, 2)
            if self.injection_time:
                self.chunk_timestamps.append(now)
                self.chunks_content.append(frame.text)
        elif isinstance(frame, OutputAudioRawFrame):
            self.audio_frames_seen += 1

        await super().process_frame(frame, direction)
        await self.push_frame(frame, direction)

async def test_v54a_r4():
    print("=" * 60)
    print(" E-ZZIO V7 — V5.4a-R4 INTERCEPT COLLECTOR CERTIFICATION")
    print("=" * 60)

    fake_tts = FakeTTS()
    real_router = EzzioRealtimeRouter()

    router_proc = EzzioRouterProcessor(router=real_router, name="router_r4")
    collector = IntermediateRouterMetricsCollector(name="collector_intermediate")
    tts_proc = EzzioTTSProcessor(tts_engine=fake_tts, name="tts_r4")

    # Placement chirurgical du collector ENTRE le Router et le TTS
    pipeline = Pipeline([router_proc, collector, tts_proc])
    worker = PipelineWorker(pipeline)
    runner = WorkerRunner()

    pipeline_ready_event = asyncio.Event()

    @worker.event_handler("on_pipeline_started")
    async def on_pipeline_started(w, frame):
        pipeline_ready_event.set()

    print("[LIFECYCLE] Démarrage du WorkerRunner...")

    async def scenario():
        try:
            await asyncio.wait_for(pipeline_ready_event.wait(), timeout=5.0)
            print("[LIFECYCLE] Pipeline READY confirmé.")
        except asyncio.TimeoutError:
            print("🔴 FAIL TIMEOUT : on_pipeline_started non reçu.")
            return

        print("[ROUTER] Injection directe d'un TextFrame ('Bonjour E-ZZIO, donne-moi un conseil court.')...")
        collector.injection_time = time.perf_counter()
        
        await worker.queue_frame(TextFrame("Bonjour E-ZZIO, donne-moi un conseil court."))

        # Attente de la réponse streaming du LLM et conversion TTS
        await asyncio.sleep(5.0)

        print("[INTERRUPTION] Injection de InterruptionFrame...")
        await worker.queue_frame(InterruptionFrame())

        await asyncio.sleep(0.5)
        print("[LIFECYCLE] Envoi de EndFrame...")
        await worker.queue_frame(EndFrame())

    try:
        await asyncio.wait_for(
            asyncio.gather(
                runner.run(worker),
                scenario()
            ),
            timeout=15.0
        )
    except asyncio.TimeoutError:
        print("🔴 FAIL TIMEOUT Global.")
        sys.exit(1)
    except Exception as e:
        print(f"🔴 EXCEPTION : {e}")
        sys.exit(1)
    finally:
        Path(fake_tts.tmp_file.name).unlink(missing_ok=True)

    inter_chunk_times = []
    for i in range(1, len(collector.chunk_timestamps)):
        dt = round((collector.chunk_timestamps[i] - collector.chunk_timestamps[i-1]) * 1000, 2)
        inter_chunk_times.append(dt)
    avg_inter_chunk = round(sum(inter_chunk_times) / len(inter_chunk_times), 2) if inter_chunk_times else 0.0

    print("\n[LIFECYCLE]")
    print(f"StartFrame          : {'PASS' if collector.start_frame_seen else 'FAIL'}")
    print(f"Pipeline READY      : {'PASS' if pipeline_ready_event.is_set() else 'FAIL'}")

    print("\n[ROUTER STREAMING - GEMMA 2:2B]")
    print(f"TTFT (First Chunk)  : {collector.first_chunk_time_ms} ms")
    print(f"Chunk count         : {len(collector.chunks_content)}")
    for idx, content in enumerate(collector.chunks_content, 1):
        print(f"Chunk #{idx}           : \"{content}\"")

    print(f"Audio frames by TTS : {collector.audio_frames_seen}")

    print("\n[TIMING]")
    print(f"Inter-chunk (avg)   : {avg_inter_chunk} ms")

    print("\n[INTERRUPTION]")
    print(f"InterruptionFrame   : {'PASS' if collector.interruption_seen else 'FAIL'}")

    passed = (
        collector.start_frame_seen and
        collector.end_frame_seen and
        collector.interruption_seen and
        len(collector.chunks_content) >= 1 and
        collector.first_chunk_time_ms is not None and
        collector.audio_frames_seen >= 1 and
        len(violations) == 0
    )

    print("\n" + "=" * 60)
    print(" V5.4a-R4 : " + ("PASS" if passed else "FAIL"))
    print("============================================================")

    if not passed:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_v54a_r4())
