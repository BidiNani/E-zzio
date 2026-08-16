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
        record = message.record
        if record["level"].no >= 30: # WARNING or higher
            # Extraction propre pour éviter les conflits de quotes
            lvl = record["level"].name
            name = record["name"]
            msg = record["message"]
            violations.append(f"[LOGURU::{lvl}] {name}: {msg}")
    logger.add(loguru_sink, level="WARNING")
except ImportError:
    pass

# --- 2. Moteurs Fakes Déterministes (0 ms I/O) ---
class FakeSTT:
    async def transcribe(self, audio_bytes):
        return {"ok": True, "text": "Ping STT Fake", "language": "fr", "confidence": 1.0}

class FakeRouter:
    async def process(self, text, task="conversation"):
        return {"ok": True, "content": "Pong Router Fake.", "model_used": "fake:0b"}

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
from pipecat.frames.frames import TextFrame, InterruptionFrame, EndFrame

from runtime.realtime.pipecat.adapter import EzzioSTTProcessor, EzzioRouterProcessor, EzzioTTSProcessor

async def test_v52_r3():
    print("=" * 80)
    print(" E-ZZIO V7 — HARNAIS V5.2-R3 (PURE LIFECYCLE & ZERO I/O)")
    print("=" * 80)

    fake_tts_engine = FakeTTS()

    stt_proc = EzzioSTTProcessor(stt_engine=FakeSTT(), name="stt_pure")
    router_proc = EzzioRouterProcessor(router=FakeRouter(), name="router_pure")
    tts_proc = EzzioTTSProcessor(tts_engine=fake_tts_engine, name="tts_pure")

    pipeline = Pipeline([stt_proc, router_proc, tts_proc])
    worker = PipelineWorker(pipeline)
    runner = WorkerRunner()

    print("[1/4] Démarrage du WorkerRunner...")

    async def scenario():
        print("[2/4] Propagation de StartFrame...")
        await asyncio.sleep(0.1)
        
        print("[3/4] Injection séquentielle : TextFrame ➔ InterruptionFrame...")
        await worker.queue_frame(TextFrame("Test de boucle pure."))
        await asyncio.sleep(0.05)
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
            timeout=3.0
        )
        elapsed = round((asyncio.get_event_loop().time() - start_time) * 1000, 2)
        print(f"\n⏱️  Temps d execution total du cycle de vie : {elapsed} ms")

    except asyncio.TimeoutError:
        print("🔴 FAIL TIMEOUT : Blocage du pipeline meme avec des Mocks !")
        sys.exit(1)
    except Exception as e:
        print(f"🔴 EXCEPTION : {e}")
        sys.exit(1)
    finally:
        Path(fake_tts_engine.tmp_file.name).unlink(missing_ok=True)

    print("\n--- AUDIT STRICT DES LOGS (LOGGING + LOGURU) ---")
    if violations:
        print("🔴 VIOLATIONS DETECTEES :")
        for v in violations:
            print(f"   - {v}")
        print("\n============================================================")
        print(" QUALIFICATION V5.2-R3 : 🔴 FAIL")
        print("============================================================")
        sys.exit(1)
    else:
        print("✅ Zero violation, zero warning Loguru, cycle de vie sain.")
        print("\n============================================================")
        print(" QUALIFICATION V5.2-R3 : 🟢 PASS (LIFECYCLE VERIFIED)")
        print("============================================================")

asyncio.run(test_v52_r3())
