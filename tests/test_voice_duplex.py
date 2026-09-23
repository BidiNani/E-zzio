"""
Tests unitaires pour le moteur vocal Duplex et l'interruption en temps réel (Barge-in).
"""

import asyncio
import struct
import time
from unittest.mock import MagicMock, patch

import pytest

from core.voice.voice_duplex_engine import DuplexState, VoiceDuplexEngine


def test_vad_speech_detection():
    engine = VoiceDuplexEngine(energy_threshold=400)

    # 1. Silence (échantillons à 0)
    silence = struct.pack("<" + "h" * 1600, *([0] * 1600))
    assert engine.detect_voice_activity(silence) is False

    # 2. Voix / Son fort (amplitude élevée)
    voice_chunk = struct.pack("<" + "h" * 1600, *([2500] * 1600))
    assert engine.detect_voice_activity(voice_chunk) is True


@pytest.mark.asyncio
async def test_barge_in_instantaneous_interruption_and_context():
    engine = VoiceDuplexEngine()

    segments = ["Bonjour,", "je suis", "en train de vous", "expliquer la solution", "en détail..."]

    # 1. Démarrage de la lecture TTS en tâche de fond
    tts_task = asyncio.create_task(engine.simulate_tts_speech(segments, delay_per_segment=0.2))
    await asyncio.sleep(0.3)  # Laisse le temps de prononcer les 2 premiers segments

    assert engine.state == DuplexState.SPEAKING

    # 2. Déclenchement de l'interruption (Barge-in de l'utilisateur)
    start_t = time.perf_counter()
    barge_res = engine.trigger_barge_in()
    interruption_delay_ms = (time.perf_counter() - start_t) * 1000

    await tts_task

    # 3. Vérification de la latence (< 50ms) et de l'état
    assert barge_res["ok"] is True
    assert barge_res["status"] == "INTERRUPTED"
    assert interruption_delay_ms < 50.0  # Coupure immédiate en sous-50ms

    # 4. Vérification de la conservation du contexte prononcé
    history = engine._conversation_history
    assert len(history) == 1
    assert "Bonjour," in history[0]["content"]
    assert "[interrompu]" in history[0]["content"]
    # Vérifie que les derniers segments n'ont pas été ajoutés inutilement
    assert "en détail..." not in history[0]["content"]


class TestDuplexExtended:
    """Tests etendus pour couvrir les branches non testees."""

    def test_detect_voice_activity_empty_or_short(self):
        engine = VoiceDuplexEngine()
        assert engine.detect_voice_activity(b"") is False
        assert engine.detect_voice_activity(b"\x00") is False

    def test_detect_voice_activity_exception(self):
        engine = VoiceDuplexEngine()
        assert engine.detect_voice_activity(b"\x00\x01\x02") is False

    def test_attach_output_stream(self):
        engine = VoiceDuplexEngine()
        stream = MagicMock()
        engine.attach_output_stream(stream)
        assert engine._output_stream is stream

    def test_barge_in_with_mock_stream_abort(self):
        engine = VoiceDuplexEngine()
        stream = MagicMock()
        stream.abort = MagicMock()
        engine.attach_output_stream(stream)
        result = engine.trigger_barge_in()
        assert stream.abort.called
        assert result["stream_cut_ms"] is not None

    def test_barge_in_with_mock_stream_stop_only(self):
        engine = VoiceDuplexEngine()
        stream = MagicMock(spec=["stop"])
        stream.stop = MagicMock()
        engine.attach_output_stream(stream)
        engine.trigger_barge_in()
        assert stream.stop.called

    def test_barge_in_stream_exception_returns_minus_one(self):
        engine = VoiceDuplexEngine()
        stream = MagicMock()
        stream.abort = MagicMock(side_effect=RuntimeError("boom"))
        engine.attach_output_stream(stream)
        result = engine.trigger_barge_in()
        assert result["stream_cut_ms"] == -1.0

    def test_barge_in_cancels_active_llm_task(self):
        engine = VoiceDuplexEngine()
        llm_task = MagicMock()
        llm_task.done = MagicMock(return_value=False)
        llm_task.cancel = MagicMock()
        engine._active_llm_task = llm_task
        engine.trigger_barge_in()
        assert llm_task.cancel.called

    @pytest.mark.asyncio
    async def test_process_incoming_audio_stream_empty(self):
        engine = VoiceDuplexEngine()

        async def empty_stream():
            return
            yield

        results = []
        async for r in engine.process_incoming_audio_stream(empty_stream()):
            results.append(r)
        assert results == []
        assert engine.state == DuplexState.LISTENING

    @pytest.mark.asyncio
    async def test_process_incoming_audio_stream_listening_speech(self):
        engine = VoiceDuplexEngine(energy_threshold=400)
        loud_chunk = struct.pack("<" + "h" * 1600, *([2500] * 1600))

        async def one_chunk_stream():
            yield loud_chunk

        results = []
        async for r in engine.process_incoming_audio_stream(one_chunk_stream()):
            results.append(r)
        assert len(results) == 1
        assert results[0]["event"] == "USER_SPEAKING"

    @pytest.mark.asyncio
    async def test_simulate_tts_speech_not_interrupted(self):
        engine = VoiceDuplexEngine()
        segments = ["a", "b", "c"]
        result = await engine.simulate_tts_speech(segments, delay_per_segment=0.01)
        assert result == "a b c"
        assert engine.state == DuplexState.IDLE
        assert len(engine._conversation_history) == 1


class TestDuplexFullCoverage:
    """Tests pour atteindre 100% de couverture sur voice_duplex_engine."""

    def test_detect_voice_activity_exception_returns_false(self):
        # Couvre L59-60 : except Exception dans detect_voice_activity
        engine = VoiceDuplexEngine()
        with patch("core.voice.voice_duplex_engine.struct.unpack", side_effect=RuntimeError("boom")):
            assert engine.detect_voice_activity(b"\x01\x02") is False

    def test_barge_in_stream_without_abort_nor_stop(self):
        # Couvre L76->78 : ni abort ni stop -> stop reste None
        # mais stream_cut_ms EST calcule (le try est entre)
        engine = VoiceDuplexEngine()

        class EmptyStream:
            pass

        engine.attach_output_stream(EmptyStream())
        result = engine.trigger_barge_in()
        # stream_cut_ms est calcule (le try est entre)
        assert result["stream_cut_ms"] is not None
        assert result["stream_cut_ms"] >= 0.0

    @pytest.mark.asyncio
    async def test_barge_in_cancels_active_tts_task(self):
        # Couvre L87 : _active_tts_task.cancel()
        engine = VoiceDuplexEngine()
        engine._active_tts_task = MagicMock()
        engine._active_tts_task.done = MagicMock(return_value=False)
        engine._active_tts_task.cancel = MagicMock()
        engine.trigger_barge_in()
        assert engine._active_tts_task.cancel.called

    @pytest.mark.asyncio
    async def test_process_incoming_stream_triggers_barge_in_while_speaking(self):
        # Couvre L124-129 : branche barge-in quand state == SPEAKING
        engine = VoiceDuplexEngine(energy_threshold=400)
        loud_chunk = struct.pack("<" + "h" * 1600, *([2500] * 1600))

        async def one_chunk_stream():
            engine.state = DuplexState.SPEAKING
            yield loud_chunk

        called = []
        def on_speech_start():
            called.append(True)

        results = []
        async for r in engine.process_incoming_audio_stream(one_chunk_stream(), on_speech_start=on_speech_start):
            results.append(r)

        assert len(results) == 1
        assert results[0]["status"] == "INTERRUPTED"
        assert called == [True]

    @pytest.mark.asyncio
    async def test_process_incoming_stream_silence_chunk(self):
        # Couvre L131->121 : boucle sans speech
        engine = VoiceDuplexEngine(energy_threshold=400)
        silent_chunk = struct.pack("<" + "h" * 1600, *([0] * 1600))

        async def two_chunks():
            yield silent_chunk
            yield silent_chunk

        results = []
        async for r in engine.process_incoming_audio_stream(two_chunks()):
            results.append(r)
        assert results == []


class TestDuplexFinalCoverage:
    """Test final pour la branche 127->129."""

    @pytest.mark.asyncio
    async def test_process_incoming_stream_speech_while_speaking_no_callback(self):
        # Couvre L126-129 : barge-in SANS callback on_speech_start
        # (branche 127->129 : on_speech_start est None)
        engine = VoiceDuplexEngine(energy_threshold=400)
        loud_chunk = struct.pack("<" + "h" * 1600, *([2500] * 1600))

        async def one_chunk_stream():
            engine.state = DuplexState.SPEAKING
            yield loud_chunk

        results = []
        async for r in engine.process_incoming_audio_stream(one_chunk_stream(), on_speech_start=None):
            results.append(r)

        assert len(results) == 1
        assert results[0]["status"] == "INTERRUPTED"
