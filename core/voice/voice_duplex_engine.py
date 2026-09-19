"""E-ZZIO Voice Runtime — Full-Duplex Voice Engine with Real-Time Barge-in.

Architecture:
- Silero / RMS Energy VAD -> Instantaneous Speech Detection
- Barge-in Interruptor -> Immediately cuts TTS audio playback & cancels in-flight LLM generation (<100ms)
- Context Continuity -> Retains spoken prefix before interruption in chat history
- Fast Model Routing -> Uses lightweight models (hermes3:8b / gemini-3.5-flash-lite) for minimal CPU turn latency
- Pure In-Memory Audio Streams -> Zero persistent audio on disk for complete privacy
"""
from __future__ import annotations

import asyncio
import logging
import struct
import time
from collections.abc import AsyncGenerator, Callable
from enum import StrEnum
from typing import Any

logger = logging.getLogger("VoiceDuplexEngine")


class DuplexState(StrEnum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"


class VoiceDuplexEngine:
    def __init__(
        self,
        sample_rate: int = 16000,
        energy_threshold: int = 450,
        fast_voice_model: str = "hermes3:8b"
    ):
        self.sample_rate = sample_rate
        self.energy_threshold = energy_threshold
        self.fast_voice_model = fast_voice_model
        self.state = DuplexState.IDLE
        self._interrupt_event = asyncio.Event()
        self._active_tts_task: asyncio.Task | None = None
        self._active_llm_task: asyncio.Task | None = None
        self._output_stream = None  # sounddevice.OutputStream (optionnel, duck-typé)
        self._spoken_text_buffer: list[str] = []
        self._conversation_history: list[dict[str, str]] = []

    def detect_voice_activity(self, audio_chunk: bytes) -> bool:
        """Détecte la présence de voix humaine dans le chunk audio (VAD instantané)."""
        if not audio_chunk or len(audio_chunk) < 2:
            return False
        try:
            count = len(audio_chunk) // 2
            shorts = struct.unpack(f"<{count}h", audio_chunk[: count * 2])
            sum_squares = sum(s * s for s in shorts)
            rms = (sum_squares / count) ** 0.5
            return rms > self.energy_threshold
        except Exception:
            return False

    def attach_output_stream(self, stream) -> None:
        """Raccorde le flux de sortie physique (sounddevice.OutputStream)."""
        self._output_stream = stream

    def trigger_barge_in(self) -> dict[str, Any]:
        """Interrompt immédiatement la parole d'E-zzio et annule la génération LLM/TTS."""
        start_t = time.perf_counter()

        # 0. Coupure physique immédiate du flux de sortie (<50ms visé)
        stream_cut_ms = None
        if self._output_stream is not None:
            try:
                t0 = time.perf_counter()
                stop = getattr(self._output_stream, "abort", None) or getattr(self._output_stream, "stop", None)
                if stop is not None:
                    stop()
                stream_cut_ms = round((time.perf_counter() - t0) * 1000, 2)
            except Exception:
                stream_cut_ms = -1.0

        # 1. Activation du signal d'interruption
        self._interrupt_event.set()

        # 2. Annulation de la tâche TTS en cours si active
        if self._active_tts_task and not self._active_tts_task.done():
            self._active_tts_task.cancel()

        # 3. Annulation de la tâche de génération LLM si active
        if self._active_llm_task and not self._active_llm_task.done():
            self._active_llm_task.cancel()

        # 4. Conservation du préfixe déjà prononcé dans l'historique
        spoken_prefix = " ".join(self._spoken_text_buffer).strip()
        if spoken_prefix:
            self._conversation_history.append({"role": "assistant", "content": f"{spoken_prefix} [interrompu]"})
            self._spoken_text_buffer.clear()

        interruption_latency_ms = round((time.perf_counter() - start_t) * 1000, 2)
        self.state = DuplexState.INTERRUPTED
        logger.info("[BARGE-IN] Interruption déclenchée avec succès en %.2f ms. État -> LISTENING", interruption_latency_ms)
        self.state = DuplexState.LISTENING

        return {
            "ok": True,
            "status": "INTERRUPTED",
            "latency_ms": interruption_latency_ms,
            "stream_cut_ms": stream_cut_ms,
            "saved_prefix": spoken_prefix
        }

    async def process_incoming_audio_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        on_speech_start: Callable[[], None] | None = None
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Traite le flux micro continu en temps réel avec détection d'interruption."""
        self.state = DuplexState.LISTENING
        self._interrupt_event.clear()

        async for chunk in audio_stream:
            is_speech = self.detect_voice_activity(chunk)

            # Si l'utilisateur parle alors qu'E-zzio est en train de parler (TTS actif)
            if is_speech and self.state == DuplexState.SPEAKING:
                barge_res = self.trigger_barge_in()
                if on_speech_start:
                    on_speech_start()
                yield barge_res

            elif is_speech and self.state == DuplexState.LISTENING:
                yield {
                    "ok": True,
                    "event": "USER_SPEAKING",
                    "chunk_bytes": len(chunk)
                }

    async def simulate_tts_speech(self, text_segments: list[str], delay_per_segment: float = 0.4) -> str:
        """Simule la lecture TTS segment par segment, interruptible à tout moment par le VAD."""
        self.state = DuplexState.SPEAKING
        self._spoken_text_buffer.clear()
        self._interrupt_event.clear()

        for segment in text_segments:
            if self._interrupt_event.is_set():
                logger.info("[TTS] Lecture stoppée net par le signal d'interruption.")
                break

            self._spoken_text_buffer.append(segment)
            await asyncio.sleep(delay_per_segment)

        spoken = " ".join(self._spoken_text_buffer)
        if not self._interrupt_event.is_set():
            self.state = DuplexState.IDLE
            self._conversation_history.append({"role": "assistant", "content": spoken})

        return spoken
