import asyncio
from typing import AsyncGenerator, Dict, Any
from .engine import KokoroEngine
from .chunker import AdaptiveStreamChunker
from .bargein import BargeInController

class AudioStreamWorker:
    def __init__(self, engine: KokoroEngine, chunker: AdaptiveStreamChunker, bargein_controller: BargeInController):
        self.engine = engine
        self.chunker = chunker
        self.bargein = bargein_controller

    async def generate_stream(
        self,
        request_id: str,
        text: str,
        voice: str = "af_bella",
        speed: float = 1.0
    ) -> AsyncGenerator[Dict[str, Any], None]:
        
        token = await self.bargein.register(request_id)
        chunks = self.chunker.chunk(text)

        try:
            for idx, chunk in enumerate(chunks):
                if token.is_cancelled():
                    event = await self.bargein.get_event(request_id)
                    yield {"status": "INTERRUPTED", "stage": "PRE_TTS_CHUNK"}
                    break

                # Propagation profonde du token
                result = await self.engine.synthesize(chunk, voice=voice, speed=speed, cancellation_token=token)

                if result.get("status") == "INTERRUPTED":
                    event = await self.bargein.get_event(request_id)
                    yield {
                        "status": "INTERRUPTED",
                        "reason": event.reason if event else "BARGE_IN",
                        "stage": result.get("stage", "UNKNOWN"),
                        "audio_frames_dropped": result.get("audio_frames_dropped", 0)
                    }
                    break

                yield {
                    "status": "STREAMING",
                    "chunk_index": idx,
                    "audio": result["audio"],
                    "ttfa": result["ttfa"]
                }
        finally:
            await self.bargein.unregister(request_id)
