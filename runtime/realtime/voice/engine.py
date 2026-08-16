import asyncio
import time
from typing import Dict, Any, Optional
from .cancellation import CancellationToken

class KokoroEngine:
    def __init__(self, kokoro_instance):
        self.kokoro = kokoro_instance

    async def synthesize(
        self, 
        text: str, 
        voice: str = "af_bella", 
        speed: float = 1.0,
        cancellation_token: Optional[CancellationToken] = None
    ) -> Dict[str, Any]:
        
        t0 = time.perf_counter()
        
        # Micro-checkpoint 1: Pre-Phonemization
        if cancellation_token and cancellation_token.is_cancelled():
            return {"status": "INTERRUPTED", "stage": "PRE_PHONEMIZATION"}

        # Executor Isolation pour le blocage C++ (ONNX)
        def blocking_onnx_call():
            try:
                stream = self.kokoro.create_stream(text, voice=voice, speed=speed)
                audio_data = []
                for chunk, sample_rate in stream:
                    audio_data.append(chunk)
                return {"audio": audio_data, "sample_rate": 24000}
            except Exception as e:
                return {"error": str(e)}

        loop = asyncio.get_running_loop()
        onnx_task = loop.run_in_executor(None, blocking_onnx_call)

        if cancellation_token:
            # ONNX Trap : Course entre l'inférence et le signal d'annulation
            cancel_task = asyncio.create_task(cancellation_token.wait())
            done, pending = await asyncio.wait(
                [onnx_task, cancel_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            if cancel_task in done:
                # Le Barge-In gagne : on abandonne le thread ONNX (Zombie géré par l'OS)
                return {
                    "status": "INTERRUPTED", 
                    "stage": "ONNX_INFERENCE",
                    "audio_frames_dropped": len(text) * 100 # Valeur métrique indicative
                }
            else:
                cancel_task.cancel() # Nettoyage si ONNX finit en premier
                result = onnx_task.result()
        else:
            result = await onnx_task

        if "error" in result:
            raise RuntimeError(f"ONNX Error: {result['error']}")

        return {
            "status": "COMPLETED",
            "audio": result.get("audio", []),
            "sample_rate": result.get("sample_rate", 24000),
            "ttfa": time.perf_counter() - t0,
            "duration": 0.0
        }
