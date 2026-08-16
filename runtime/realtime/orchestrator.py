import asyncio
import re
from typing import AsyncGenerator, Dict, Any

from .brain.router import BrainProviderRouter
from .brain.contracts import BrainRequest
from .voice.engine import KokoroEngine
from .voice.bargein import BargeInController

class DialogueOrchestrator:
    """Chef d'orchestre E-ZZIO : connecte le flux de tokens LLM au pipeline TTS avec buffering dynamique."""
    
    def __init__(self, brain: BrainProviderRouter, voice: KokoroEngine, bargein: BargeInController):
        self.brain = brain
        self.voice = voice
        self.bargein = bargein

    async def process_turn(self, request_id: str, user_text: str) -> AsyncGenerator[Dict[str, Any], None]:
        token = await self.bargein.register(request_id)
        brain_req = BrainRequest(request_id=request_id, text=user_text)

        sentence_buffer = ""
        chunk_index = 0

        try:
            async for brain_chunk in self.brain.ask_stream(brain_req, token):
                # 1. Coupure ultra-précoce au niveau du LLM
                if token.is_cancelled():
                    event = await self.bargein.get_event(request_id)
                    yield {
                        "status": "INTERRUPTED",
                        "reason": event.reason if event else "UNKNOWN",
                        "stage": "BRAIN_STREAM"
                    }
                    break

                sentence_buffer += brain_chunk.chunk_text
                
                # 2. Détection dynamique de fin de phrase
                is_boundary = bool(re.search(r'[.!?]\s*$', sentence_buffer))
                
                if brain_chunk.is_final or is_boundary:
                    text_to_speak = sentence_buffer.strip()
                    sentence_buffer = ""
                    
                    if text_to_speak:
                        # 3. Coupure juste avant l'inférence ONNX
                        if token.is_cancelled():
                            yield {"status": "INTERRUPTED", "stage": "PRE_TTS"}
                            break
                            
                        # 4. Synthèse audio du chunk sémantique
                        audio_res = await self.voice.synthesize(text_to_speak)
                        
                        yield {
                            "status": "AUDIO_CHUNK_READY",
                            "chunk_index": chunk_index,
                            "text_chunk": text_to_speak,
                            "audio_duration": audio_res["duration"],
                            "tts_ttfa": audio_res["ttfa"]
                        }
                        chunk_index += 1
                        
        finally:
            await self.bargein.unregister(request_id)
