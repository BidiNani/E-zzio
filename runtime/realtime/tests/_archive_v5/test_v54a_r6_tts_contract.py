import sys
import asyncio
import logging
import time
import tempfile
import wave
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

class FakeTTS_ValidWAV:
    def __init__(self):
        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        self.tmp_file.close() 
        with wave.open(self.tmp_file.name, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b'\x00' * 3200)

    async def synthesize(self, text):
        await asyncio.sleep(0.15)
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
    ErrorFrame,
    InterruptionFrame,
    EndFrame
)

from runtime.realtime.pipecat.adapter import (
    EzzioRouterProcessor,
    EzzioTTSProcessor
)

class PreTTSCollector(FrameProcessor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.injection_time = None
        self.text_frames = []

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        if isinstance(frame, TextFrame) and self.injection_time:
            self.text_frames.append(time.perf_counter())
        await super().process_frame(frame, direction)
        await self.push_frame(frame, direction)

class PostTTSCollector(FrameProcessor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.all_frames = []
        self.audio_frames = []
        self.error_frames = []

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        now = time.perf_counter()
        frame_name = type(frame).__name__
        self.all_frames.append(frame_name)
        
        if isinstance(frame, OutputAudioRawFrame):
            self.audio_frames.append(now)
        elif isinstance(frame, ErrorFrame):
            self.error_frames.append(frame.error)
            
        await super().process_frame(frame, direction)
        await self.push_frame(frame, direction)

async def test_v54a_r6():
    print("=" * 60)
    print(" E-ZZIO V7 — V5.4a-R6 TTS BOUNDARY CERTIFICATION")
    print("=" * 60)

    fake_tts = FakeTTS_ValidWAV()
    real_router = EzzioRealtimeRouter()

    router_proc = EzzioRouterProcessor(router=real_router, name="router_r6")
    pre_collector = PreTTSCollector(name="collector_pre_tts")
    tts_proc = EzzioTTSProcessor(tts_engine=fake_tts, name="tts_r6")
    post_collector = PostTTSCollector(name="collector_post_tts")

    pipeline = Pipeline([router_proc, pre_collector, tts_proc, post_collector])
    worker = PipelineWorker(pipeline)
    runner = WorkerRunner()

    pipeline_ready = asyncio.Event()

    @worker.event_handler("on_pipeline_started")
    async def on_pipeline_started(w, frame):
        pipeline_ready.set()

    print("[LIFECYCLE] Démarrage du WorkerRunner...")

    async def scenario():
        try:
            await asyncio.wait_for(pipeline_ready.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            return

        print("[ROUTER] Injection du TextFrame...")
        pre_collector.injection_time = time.perf_counter()
        
        # PROMPT EXPLICITE GARANTISSANT UNE RÉPONSE DE GEMMA
        await worker.queue_frame(TextFrame("Bonjour E-ZZIO, donne-moi un conseil court."))

        await asyncio.sleep(5.0)
        print("[INTERRUPTION] Injection InterruptionFrame...")
        await worker.queue_frame(InterruptionFrame())

        await asyncio.sleep(0.5)
        print("[LIFECYCLE] Envoi EndFrame...")
        await worker.queue_frame(EndFrame())

    try:
        await asyncio.wait_for(
            asyncio.gather(runner.run(worker), scenario()),
            timeout=15.0
        )
    except Exception as e:
        print(f"🔴 EXCEPTION FATALE : {e}")
        sys.exit(1)
    finally:
        Path(fake_tts.tmp_file.name).unlink(missing_ok=True)

    ttft_ms = round((pre_collector.text_frames[0] - pre_collector.injection_time) * 1000, 2) if pre_collector.text_frames else None
    
    tts_latency_ms = None
    if pre_collector.text_frames and post_collector.audio_frames:
        tts_latency_ms = round((post_collector.audio_frames[0] - pre_collector.text_frames[0]) * 1000, 2)
        
    total_pipeline_time_ms = round((post_collector.audio_frames[0] - pre_collector.injection_time) * 1000, 2) if post_collector.audio_frames else None

    print("\n[ROUTER -> PRE-TTS]")
    print(f"TTFT (Gemma 2:2B)   : {ttft_ms} ms")
    print(f"TextFrames reçus    : {len(pre_collector.text_frames)}")

    print("\n[TTS -> POST-TTS]")
    print(f"AudioFrames générés : {len(post_collector.audio_frames)}")
    print(f"ErrorFrames générés : {len(post_collector.error_frames)}")
    if post_collector.error_frames:
        print(f"Erreurs             : {post_collector.error_frames}")
    print(f"Séquence de sortie  : {', '.join(post_collector.all_frames)}")

    print("\n[LATENCES]")
    print(f"Temps TTFT LLM      : {ttft_ms or 'N/A'} ms")
    print(f"Surcharge Fake TTS  : {tts_latency_ms or 'N/A'} ms")
    print(f"Tps Total T0->Audio : {total_pipeline_time_ms or 'N/A'} ms")

    passed = (
        len(pre_collector.text_frames) > 0 and
        len(post_collector.audio_frames) > 0 and
        len(post_collector.error_frames) == 0 and
        len(violations) == 0
    )

    print("\n" + "=" * 60)
    print(" V5.4a-R6 : " + ("PASS" if passed else "FAIL"))
    print("============================================================")

    if not passed:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_v54a_r6())
