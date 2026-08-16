import asyncio
import logging
import os
import time
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineWorker
from pipecat.workers.runner import WorkerRunner
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import OutputAudioRawFrame, TextFrame, EndFrame
# Importation précise pour Pipecat 1.7.0
from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService

# --- Instrumentation minimale ---
class ForensicCollector(FrameProcessor):
    def __init__(self):
        super().__init__()
        self.t0 = None
        self.first_audio = None
        self.audio_received = False

    async def process_frame(self, frame, direction):
        now = time.perf_counter()
        if isinstance(frame, OutputAudioRawFrame) and not self.first_audio:
            self.first_audio = now
            self.audio_received = True
            print(f"✅ PREMIER AUDIO REÇU à {round((now - self.t0)*1000, 2)} ms")
        await super().process_frame(frame, direction)
        await self.push_frame(frame, direction)

async def test_v56_b():
    print("--- DÉMARRAGE QUALIFICATION FORENSIQUE GEMINI LIVE ---")
    
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    
    # Configuration du service LLM Live
    gemini_live = GeminiLiveLLMService(
        api_key=api_key,
        model="gemini-3.1-flash-live-preview", # Modèle cible
        voice_id="Puck"
    )

    collector = ForensicCollector()
    pipeline = Pipeline([gemini_live, collector])
    worker = PipelineWorker(pipeline)
    runner = WorkerRunner()

    @worker.event_handler("on_pipeline_started")
    async def on_start(w, f):
        print("✅ Pipeline Started & WebSocket Connected")
        collector.t0 = time.perf_counter()
        await w.queue_frame(TextFrame("Dis uniquement 'E-ZZIO V7 en ligne'."))

    try:
        await runner.run(worker)
    except Exception as e:
        print(f"🔴 Exception : {e}")

if __name__ == "__main__":
    asyncio.run(test_v56_b())
