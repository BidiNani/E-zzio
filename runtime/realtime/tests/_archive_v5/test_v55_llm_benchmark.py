import sys
import asyncio
import logging
import time
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

# Importation des VRAIS moteurs E-ZZIO
from runtime.realtime.pipecat.router import EzzioRealtimeRouter
from runtime.realtime.audio.tts import EzzioTTS

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineWorker
from pipecat.workers.runner import WorkerRunner
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import (
    Frame, StartFrame, TextFrame, OutputAudioRawFrame, ErrorFrame, EndFrame
)
from runtime.realtime.pipecat.adapter import EzzioRouterProcessor, EzzioTTSProcessor

class BenchmarkCollector(FrameProcessor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.t0_injection = None
        self.t_first_text = None
        self.t_first_audio = None
        self.text_chunks = 0
        self.audio_frames = 0
        self.errors = 0

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        now = time.perf_counter()
        
        if isinstance(frame, TextFrame) and self.t0_injection and not self.t_first_text:
            self.t_first_text = now
        
        if isinstance(frame, TextFrame) and self.t0_injection:
            self.text_chunks += 1

        if isinstance(frame, OutputAudioRawFrame) and self.t0_injection and not self.t_first_audio:
            self.t_first_audio = now
            
        if isinstance(frame, OutputAudioRawFrame) and self.t0_injection:
            self.audio_frames += 1

        if isinstance(frame, ErrorFrame):
            self.errors += 1

        await super().process_frame(frame, direction)
        await self.push_frame(frame, direction)

async def run_benchmark(prompt_text: str):
    print("=" * 60)
    print(" E-ZZIO V7 — V5.5 REAL-TIME PIPELINE BENCHMARK")
    print("=" * 60)
    print(f"[PROMPT] \"{prompt_text}\"\n")

    # Instanciation des VRAIS moteurs (Assure-toi que Piper est accessible)
    real_router = EzzioRealtimeRouter()
    real_tts = EzzioTTS()

    router_proc = EzzioRouterProcessor(router=real_router, name="router_bench")
    tts_proc = EzzioTTSProcessor(tts_engine=real_tts, name="tts_bench")
    collector = BenchmarkCollector(name="collector_bench")

    # Ordre : Router -> TTS -> Collector (pour voir la sortie audio)
    pipeline = Pipeline([router_proc, tts_proc, collector])
    worker = PipelineWorker(pipeline)
    runner = WorkerRunner()

    pipeline_ready = asyncio.Event()

    @worker.event_handler("on_pipeline_started")
    async def on_pipeline_started(w, frame):
        pipeline_ready.set()

    async def scenario():
        try:
            await asyncio.wait_for(pipeline_ready.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            print("🔴 FAIL TIMEOUT : Initialisation Pipeline")
            return

        print("[TEST] Pipeline Ready. Injection du prompt...")
        collector.t0_injection = time.perf_counter()
        await worker.queue_frame(TextFrame(prompt_text))

        # Attente généreuse pour le traitement réel
        await asyncio.sleep(10.0)
        await worker.queue_frame(EndFrame())

    try:
        await asyncio.wait_for(
            asyncio.gather(runner.run(worker), scenario()),
            timeout=25.0
        )
    except Exception as e:
        print(f"🔴 EXCEPTION FATALE : {e}")
        sys.exit(1)

    ttft_ms = round((collector.t_first_text - collector.t0_injection) * 1000, 2) if collector.t_first_text else "N/A"
    ttfa_ms = round((collector.t_first_audio - collector.t0_injection) * 1000, 2) if collector.t_first_audio else "N/A"
    tts_overhead_ms = round((collector.t_first_audio - collector.t_first_text) * 1000, 2) if (collector.t_first_audio and collector.t_first_text) else "N/A"

    print("\n[PERFORMANCES]")
    print(f"TTFT (Time To First Token) : {ttft_ms} ms")
    print(f"TTFA (Time To First Audio) : {ttfa_ms} ms")
    print(f"TTS Overhead (Audio-Text)  : {tts_overhead_ms} ms")
    
    print("\n[VOLUMÉTRIE]")
    print(f"Text Chunks générés        : {collector.text_chunks}")
    print(f"Audio Frames générés       : {collector.audio_frames}")
    
    print("\n[STABILITÉ]")
    print(f"Erreurs de flux (Errors)   : {collector.errors}")
    print(f"Warnings/Violations (Logs) : {len(violations)}")

    passed = (
        collector.t_first_text is not None and
        collector.t_first_audio is not None and
        collector.errors == 0 and
        len(violations) == 0
    )

    print("\n" + "=" * 60)
    print(" V5.5 BENCHMARK : " + ("PASS" if passed else "FAIL"))
    print("============================================================")

    if not passed:
        sys.exit(1)

if __name__ == "__main__":
    # Test avec une demande courte pour forcer un TTFT optimal
    asyncio.run(run_benchmark("Donne-moi une définition très courte de la gravité."))
