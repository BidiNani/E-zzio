import sys
import asyncio
import logging
import tempfile
from pathlib import Path

sys.path.insert(0, r'G:\AI\E-zzio')

# --- 1. Trap de Logs Hybride (Standard Logging + Loguru) ---
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
        if rec["level"].no >= 30: # WARNING or higher
            lvl = rec["level"].name
            name = rec["name"]
            msg = rec["message"]
            violations.append(f"[LOGURU::{lvl}] {name}: {msg}")
    logger.add(loguru_sink, level="WARNING")
except ImportError:
    pass

# --- 2. Moteurs Fakes Déterministes pour V5.3 ---
class FakeSTT:
    async def transcribe(self, audio_bytes):
        return {"ok": True, "text": "Bonjour E-ZZIO, validation de flux.", "language": "fr", "confidence": 0.99}

class FakeRouter:
    async def process(self, text, task="conversation"):
        return {"ok": True, "content": "Bonjour ! Flux reçu et validé.", "model_used": "fake_router:v7"}

class FakeTTS:
    def __init__(self):
        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        self.tmp_file.write(b'\x00' * 3200) # 3200 octets = ~100ms PCM 16kHz
        self.tmp_file.close()

    async def synthesize(self, text):
        return {"ok": True, "audio_path": self.tmp_file.name, "duration": 0.1}

# --- 3. Processor de Collecte & d'Inspection au Sink ---
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineWorker
from pipecat.workers.runner import WorkerRunner
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import (
    Frame,
    StartFrame,
    InputAudioRawFrame,
    OutputAudioRawFrame,
    TextFrame,
    InterruptionFrame,
    EndFrame
)

from runtime.realtime.pipecat.adapter import (
    EzzioSTTProcessor,
    EzzioRouterProcessor,
    EzzioTTSProcessor
)

class FrameCollectorProcessor(FrameProcessor):
    """Processeur d'inspection placé en fin de pipeline pour enregistrer le flux exact."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.history = []

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        self.history.append((type(frame).__name__, frame))
        await self.push_frame(frame, direction)

async def test_v53():
    print("=" * 80)
    print(" E-ZZIO V7 — HARNAIS DE CERTIFICATION V5.3 (REAL FRAME FLOW)")
    print("=" * 80)

    fake_tts = FakeTTS()
    stt_proc = EzzioSTTProcessor(stt_engine=FakeSTT(), name="stt_v53")
    router_proc = EzzioRouterProcessor(router=FakeRouter(), name="router_v53")
    tts_proc = EzzioTTSProcessor(tts_engine=fake_tts, name="tts_v53")
    collector = FrameCollectorProcessor(name="collector_v53")

    pipeline = Pipeline([stt_proc, router_proc, tts_proc, collector])
    worker = PipelineWorker(pipeline)
    runner = WorkerRunner()

    print("[1/4] Démarrage du WorkerRunner & propagation de StartFrame...")

    async def scenario():
        await asyncio.sleep(0.1)
        
        print("[2/4] Injection d un InputAudioRawFrame (Simulation Micro)...")
        raw_audio = b'\x00' * 1600 # 50ms audio dummy
        await worker.queue_frame(InputAudioRawFrame(audio=raw_audio, sample_rate=16000, num_channels=1))

        await asyncio.sleep(0.1)

        print("[3/4] Injection d une InterruptionFrame (Simulation Barge-in)...")
        await worker.queue_frame(InterruptionFrame())

        await asyncio.sleep(0.1)

        print("[4/4] Clôture par EndFrame...")
        await worker.queue_frame(EndFrame())

    start_time = asyncio.get_event_loop().time()

    try:
        await asyncio.wait_for(
            asyncio.gather(
                runner.run(worker),
                scenario()
            ),
            timeout=4.0
        )
        elapsed = round((asyncio.get_event_loop().time() - start_time) * 1000, 2)
        print(f"\n⏱️  Temps d execution du flux complet : {elapsed} ms")

    except asyncio.TimeoutError:
        print("🔴 FAIL TIMEOUT : Le flux de frames est resté bloqué.")
        sys.exit(1)
    except Exception as e:
        print(f"🔴 EXCEPTION : {e}")
        sys.exit(1)
    finally:
        Path(fake_tts.tmp_file.name).unlink(missing_ok=True)

    print("\n--- INSPECTION DU FLUX EN SORTIE DU SINK ---")
    frame_names = [item[0] for item in collector.history]
    print(f"Séquence capturée ({len(frame_names)} trames) :")
    for i, name in enumerate(frame_names, 1):
        print(f"  {i}. {name}")

    # Assertions de qualification
    assert "StartFrame" in frame_names, "StartFrame manquant en sortie de pipeline !"
    assert "OutputAudioRawFrame" in frame_names, "OutputAudioRawFrame manquant (EzzioTTS n a pas généré d audio sortant) !"
    assert "InterruptionFrame" in frame_names, "InterruptionFrame manquant en sortie !"
    assert "EndFrame" in frame_names, "EndFrame manquant en sortie !"

    print("\n--- AUDIT DES LOGS (LOGGING + LOGURU) ---")
    if violations:
        print("🔴 VIOLATIONS DETECTEES :")
        for v in violations:
            print(f"   - {v}")
        print("\n============================================================")
        print(" QUALIFICATION V5.3 : 🔴 FAIL")
        print("============================================================")
        sys.exit(1)
    else:
        print("✅ Flux de trames intègre, transformations validées, zero warning.")
        print("============================================================")
        print(" QUALIFICATION V5.3 : 🟢 PASS (REAL FRAME FLOW CERTIFIED)")
        print("============================================================")

if __name__ == "__main__":
    asyncio.run(test_v53())
