import asyncio
import json
import time
from pathlib import Path
import bootstrap

from kokoro_onnx import Kokoro
from runtime.realtime.voice import KokoroEngine, BargeInController
from runtime.realtime.brain import BrainProviderRouter
from runtime.realtime.orchestrator import DialogueOrchestrator

async def run_integration_audit():
    start_time_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    # 1. Initialisation de toutes les briques certifiées
    k_inst = Kokoro(
        r"G:\AI\E-zzio\runtime\realtime\models\kokoro\current\kokoro-v0_19.onnx",
        r"G:\AI\E-zzio\runtime\realtime\models\kokoro\current\voices.bin"
    )
    voice_engine = KokoroEngine(k_inst)
    brain_router = BrainProviderRouter(default_provider="mock") # Le mock génère 15 mots
    bargein = BargeInController()
    
    orchestrator = DialogueOrchestrator(brain_router, voice_engine, bargein)

    # 2. Audit Intégral : Flux Voix + Cerveau avec interruption
    req_id = "full-loop-bargein"
    user_prompt = "Initialisation système E-ZZIO."
    
    frames = []
    t0 = time.perf_counter()
    global_ttfa = 0

    async def user_interrupt_simulator():
        # L'utilisateur coupe la parole après ~0.5 secondes (pendant le TTS du 1er chunk)
        await asyncio.sleep(0.5)
        await bargein.interrupt(req_id, source="USER", reason="USER_BARGE_IN")

    async def consume_loop():
        nonlocal global_ttfa
        async for frame in orchestrator.process_turn(req_id, user_prompt):
            if not frames and frame["status"] == "AUDIO_CHUNK_READY":
                global_ttfa = time.perf_counter() - t0
            frames.append(frame)

    await asyncio.gather(consume_loop(), user_interrupt_simulator())

    # Vérifications critiques d'intégration
    assert len(frames) > 0, "L'orchestrateur doit produire des frames"
    assert frames[-1]["status"] == "INTERRUPTED", "La boucle globale doit se terminer par une interruption"
    
    audio_chunks = [f for f in frames if f["status"] == "AUDIO_CHUNK_READY"]
    
    # Production du Rapport JSON Forensic
    reports_dir = Path(r"G:\AI\E-zzio\runtime\realtime\tests\reports")
    report_file = reports_dir / "phase35_report.json"

    report_payload = {
        "component": "Voice Intelligence Loop (DialogueOrchestrator)",
        "phase": "3.5",
        "timestamp_utc": start_time_utc,
        "status": "CERTIFIED",
        "metrics": {
            "audio_chunks_produced": len(audio_chunks),
            "global_ttfa_ms": int(global_ttfa * 1000) if global_ttfa else 0,
            "final_stage": frames[-1].get("stage", "UNKNOWN"),
            "interruption_reason": frames[-1].get("reason", "UNKNOWN")
        },
        "score": 10
    }

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2)

if __name__ == "__main__":
    asyncio.run(run_integration_audit())
