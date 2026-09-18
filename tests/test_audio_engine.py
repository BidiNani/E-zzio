"""
Tests unitaires pour le double moteur audio (Faster-Whisper Batch & Nemotron-3.5-ASR Streaming).
"""

import struct
import wave

import pytest

from core.perception.audio_engine import AudioTranscriptionEngine, NemotronStreamingASR


def test_audio_engine_lazy_loading():
    """Vérifie qu'aucun moteur n'est chargé en mémoire avant son premier appel réel."""
    engine = AudioTranscriptionEngine()
    assert engine._whisper_model is None
    assert engine.nemotron._model is None


def test_nemotron_streaming_chunks():
    """Vérifie la transcription en streaming chunk par chunk via Nemotron-3.5-ASR."""
    nemotron = NemotronStreamingASR(chunk_duration_ms=560)

    # Simulation d'un flux audio reçu par chunks de 560ms (44.1kHz 16-bit)
    sample_rate = 16000
    chunk_bytes = struct.pack("<" + "h" * 8960, *([100] * 8960))

    # Chunk 1
    res1 = nemotron.transcribe_chunk(chunk_bytes, session_id="live_mic_1", is_last=False)
    assert res1["ok"] is True
    assert res1["engine"] == "nemotron-3.5-asr-streaming"
    assert res1["chunk_index"] == 1
    assert res1["is_last"] is False

    # Chunk 2 (Fin de flux)
    res2 = nemotron.transcribe_chunk(chunk_bytes, session_id="live_mic_1", is_last=True)
    assert res2["ok"] is True
    assert res2["chunk_index"] == 2
    assert res2["is_last"] is True


def test_audio_engine_auto_routing_and_batch(tmp_path):
    """Vérifie le routage automatique : Fichier -> Faster-Whisper, Octets bruts -> Nemotron."""
    engine = AudioTranscriptionEngine(whisper_model_size="tiny")

    # 1. Routage Flux brut -> Nemotron Streaming
    raw_audio_stream = struct.pack("<" + "h" * 4000, *([50] * 4000))
    res_stream = engine.transcribe(raw_audio_stream, mode="auto")
    assert res_stream["ok"] is True
    assert res_stream["engine"] == "nemotron-3.5-asr-streaming"

    # 2. Routage Fichier disque -> Faster-Whisper Batch
    wav_path = tmp_path / "sample_note.wav"
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(struct.pack("<" + "h" * 16000, *([0] * 16000)))

    res_batch = engine.transcribe(wav_path, mode="auto")
    assert res_batch["ok"] is True
    assert res_batch["engine"] == "faster-whisper-batch"
    assert "duration_seconds" in res_batch
