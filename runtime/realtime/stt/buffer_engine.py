import asyncio
import time
import numpy as np
from typing import Dict, Any, Optional
from .provider import ISttProvider, SttResult

class SpeechBufferEngine:
    def __init__(self, stt_provider: ISttProvider):
        self.stt_provider = stt_provider
        self._buffer = []
        self._is_open = False
        self._lock = asyncio.Lock()
        self.metrics_audit = {
            "buffers_opened": 0,
            "buffers_frozen": 0,
            "chunks_accumulated": 0,
            "errors_isolated": 0
        }

    async def process_vad_frame(self, vad_frame: Dict[str, Any]) -> Optional[SttResult]:
        event = vad_frame.get("event")
        audio_chunk = vad_frame.get("audio")

        async with self._lock:
            if event == "SPEECH_STARTED":
                self._buffer = []
                self._is_open = True
                self.metrics_audit["buffers_opened"] += 1
                if audio_chunk is not None:
                    self._buffer.append(audio_chunk.copy())
                    self.metrics_audit["chunks_accumulated"] += 1

            elif event == "SPEECH_ONGOING" and self._is_open:
                if audio_chunk is not None:
                    self._buffer.append(audio_chunk.copy())
                    self.metrics_audit["chunks_accumulated"] += 1

            elif event == "SPEECH_ENDED" and self._is_open:
                if audio_chunk is not None:
                    self._buffer.append(audio_chunk.copy())
                    self.metrics_audit["chunks_accumulated"] += 1
                
                self._is_open = False
                self.metrics_audit["buffers_frozen"] += 1
                
                if self._buffer:
                    frozen_audio = np.concatenate([c.flatten() for c in self._buffer])
                    self._buffer = []
                    try:
                        result = await self.stt_provider.transcribe(frozen_audio, sample_rate=16000)
                        return result
                    except Exception:
                        self.metrics_audit["errors_isolated"] += 1
                        return None
        return None
