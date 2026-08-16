import asyncio
import json
import time
import uuid
from pathlib import Path
import bootstrap

from kokoro_onnx import Kokoro
from runtime.realtime.voice import KokoroEngine, BargeInController
from runtime.realtime.brain import BrainProviderRouter
from runtime.realtime.brain.providers import IBrainProvider
from runtime.realtime.brain.contracts import BrainResponseChunk, BrainRequest
from runtime.realtime.orchestrator import DialogueOrchestrator

class DuplexMockProvider(IBrainProvider):
    """Mock générant 4 phrases distinctes pour forcer le buffer TTS à travailler."""
    async def generate_stream(self, request, cancel_token):
        sentences = [
            "Initialisation du système E-ZZIO.",
            "Chargement des modules vocaux terminé.",
            "Connexion au réseau neuronal établie.",
            "Prêt pour le déploiement asynchrone."
        ]
        text = " ".join(sentences)
        words = text.split(" ")
        
        for i, word in enumerate(words):
            if cancel_token.is_cancelled():
                yield BrainResponseChunk(request.request_id, "", True, "INTERRUPTED")
                return
            await asyncio.sleep(0.01) # Vitesse de génération LLM simulée
            is_final = (i == len(words) - 1)
            yield BrainResponseChunk(request.request_id, word + " ", is_final, "COMPLETED" if is_final else "GENERATING")

async def run_forensic_audit():
    start_time_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    k_inst = Kokoro(
        r"G:\AI\E-zzio\runtime\realtime\models\kokoro\current\kokoro-v0_19.onnx",
        r"G:\AI\E-zzio\runtime\realtime\models\kokoro\current\voices.bin"
    )
    voice_engine = KokoroEngine(k_inst)
    bargein = BargeInController()
    
    router = BrainProviderRouter()
    router.register_provider("duplex", DuplexMockProvider())
    router.default_provider_name = "duplex"
    
    orchestrator = DialogueOrchestrator(router, voice_engine, bargein)
    
    req_id = "test-duplex-001"
    frames = []
    t0 = time.perf_counter()
    global_ttfa = 0
    audio_chunks = 0
    
    async for frame in orchestrator.process_turn(req_id, "SYSTEM_TEST"):
        frames.append(frame)
        if frame["status"] == "AUDIO_CHUNK_READY":
            if audio_chunks == 0:
                global_ttfa = time.perf_counter() - t0
            
            audio_chunks += 1
            
            # [CRITICAL BARGE-IN POINT] : On coupe dès que le 1er chunk audio est sorti
            if audio_chunks == 1:
                await bargein.interrupt(req_id, source="USER", reason="BARGE_IN_DURING_TTS")
                
        elif frame["status"] == "INTERRUPTED":
            break # Validation de la sortie de boucle
            
    total_time = time.perf_counter() - t0
    
    # Assertions de sécurité (Fail-Closed)
    assert audio_chunks > 0, "FATAL: Aucun chunk audio n'a été produit."
    assert frames[-1]["status"] == "INTERRUPTED", "FATAL: Le flux n'a pas propagé l'état INTERRUPTED."
    
    # Métriques
    prevented = 4 - audio_chunks # 4 phrases prévues, 1 lue, 3 économisées
    
    report = {
        "component": "Full Duplex Voice Loop",
        "phase": "3.5.1",
        "timestamp_utc": start_time_utc,
        "status": "CERTIFIED" if (audio_chunks == 1 and prevented == 3) else "FAILED",
        "metrics": {
            "tts_chunks_produced": audio_chunks,
            "prevented_tts_chunks": prevented,
            "global_ttfa_ms": int(global_ttfa * 1000),
            "total_latency_ms": int(total_time * 1000),
            "cutoff_stage": frames[-1].get("stage", "UNKNOWN")
        },
        "score": 10 if (audio_chunks == 1 and prevented == 3) else 0
    }
    
    report_file = Path(r"G:\AI\E-zzio\runtime\realtime\tests\reports\phase351_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    asyncio.run(run_forensic_audit())
