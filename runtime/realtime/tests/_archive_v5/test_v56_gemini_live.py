import sys
import asyncio
import logging
import time
import os
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

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineWorker
from pipecat.workers.runner import WorkerRunner
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import (
    Frame, StartFrame, OutputAudioRawFrame, TextFrame, EndFrame, ErrorFrame
)

# CHEMIN D'IMPORTATION VALIDÉ POUR PIPECAT 1.7.0
from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService

class LiveMetricsCollector(FrameProcessor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.t0_injection = None
        self.t_first_audio = None
        self.audio_chunks = 0
        self.text_transcripts = []
        self.errors = []

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        now = time.perf_counter()
        
        if isinstance(frame, OutputAudioRawFrame) and self.t0_injection and not self.t_first_audio:
            self.t_first_audio = now
            
        if isinstance(frame, OutputAudioRawFrame) and self.t0_injection:
            self.audio_chunks += 1

        if isinstance(frame, TextFrame):
            self.text_transcripts.append(frame.text)

        if isinstance(frame, ErrorFrame):
            self.errors.append(frame.error)

        await super().process_frame(frame, direction)
        await self.push_frame(frame, direction)

async def test_v56_a():
    print("=" * 60)
    print(" E-ZZIO V7 — V5.6-A GEMINI LIVE BENCHMARK")
    print("=" * 60)

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("🔴 FAIL : Variable GEMINI_API_KEY ou GOOGLE_API_KEY manquante.")
        sys.exit(1)

    # Initialisation du service Speech-to-Speech natif
    gemini_live = GeminiLiveLLMService(
        api_key=api_key
    )

    collector = LiveMetricsCollector(name="collector_live_a")
    pipeline = Pipeline([gemini_live, collector])
    worker = PipelineWorker(pipeline)
    runner = WorkerRunner()

    pipeline_ready = asyncio.Event()

    @worker.event_handler("on_pipeline_started")
    async def on_pipeline_started(w, frame):
        pipeline_ready.set()

    async def scenario():
        try:
            await asyncio.wait_for(pipeline_ready.wait(), timeout=10.0)
            print("[LIFECYCLE] Pipeline Ready. Session Gemini Live établie.")
        except asyncio.TimeoutError:
            print("🔴 FAIL TIMEOUT : Échec d'initialisation de la session Live.")
            return

        print("[TEST] Injection de la consigne textuelle...")
        collector.t0_injection = time.perf_counter()
        await worker.queue_frame(TextFrame("Dis uniquement 'E-ZZIO V7 en ligne' de manière dynamique."))

        await asyncio.sleep(6.0)
        await worker.queue_frame(EndFrame())

    try:
        await asyncio.wait_for(
            asyncio.gather(runner.run(worker), scenario()),
            timeout=20.0
        )
    except Exception as e:
        print(f"🔴 EXCEPTION FATALE : {e}")
        sys.exit(1)

    ttfa_ms = round((collector.t_first_audio - collector.t0_injection) * 1000, 2) if collector.t_first_audio else "N/A"

    print("\n[PERFORMANCES GEMINI LIVE]")
    print(f"TTFA (Time To First Audio) : {ttfa_ms} ms")
    print(f"Audio Chunks reçus         : {collector.audio_chunks}")
    print(f"Transcriptions capturées   : {collector.text_transcripts}")

    print("\n[AUDIT DE STABILITÉ]")
    print(f"Erreurs API / Stream       : {collector.errors}")
    print(f"Warnings/Violations Logs   : {len(violations)}")

    passed = (
        collector.t_first_audio is not None and
        collector.audio_chunks > 0 and
        len(collector.errors) == 0 and
        len(violations) == 0
    )

    print("\n" + "=" * 60)
    print(" V5.6-A GEMINI LIVE : " + ("PASS" if passed else "FAIL"))
    print("============================================================")

    if not passed:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_v56_a())
