import io
import struct
import wave

import pytest

from core.voice.voice_gateway import VoiceGateway, VoiceState


@pytest.fixture
def voice_gateway():
    return VoiceGateway(sample_rate=16000, energy_threshold=400)


def test_voice_gateway_init_and_status(voice_gateway):
    status = voice_gateway.get_status()
    assert status["state"] == "idle"
    assert status["sample_rate"] == 16000
    assert status["energy_threshold"] == 400


def test_vad_speech_detection(voice_gateway):
    # 1. Silence (échantillons à 0)
    silence = b"\x00" * 3200
    assert voice_gateway.detect_speech(silence) is False

    # 2. Signal fort (PCM 16-bit)
    loud_samples = [1000] * 1600
    loud_data = struct.pack(f"<{len(loud_samples)}h", *loud_samples)
    assert voice_gateway.detect_speech(loud_data) is True


@pytest.mark.asyncio
async def test_transcription_stt(voice_gateway):
    sample_audio = b"\x00" * 16000
    res = await voice_gateway.transcribe(sample_audio, language="fr")
    assert res["status"] == "success"
    assert "text" in res
    assert res["duration_sec"] > 0
    assert res["language"] == "fr"

    # Audio vide
    empty_res = await voice_gateway.transcribe(b"")
    assert empty_res["status"] == "empty"
    assert empty_res["text"] == ""


@pytest.mark.asyncio
async def test_synthesis_tts(voice_gateway):
    audio_out = await voice_gateway.synthesize("Bonjour E-ZZIO, ceci est un test de synthèse vocale.")
    assert len(audio_out) > 44  # En-tête WAV minimale

    # Vérification que c'est un WAV valide
    with wave.open(io.BytesIO(audio_out), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000


@pytest.mark.asyncio
async def test_voice_interaction_e2e_flow(voice_gateway):
    from unittest.mock import AsyncMock, MagicMock

    mock_core = MagicMock(spec=["think"])
    mock_core.think = AsyncMock(return_value={
        "response": "Ordre vocal bien reçu et exécuté.",
        "intent": "voice_command",
        "provider": "ollama"
    })

    sample_audio = b"\x00" * 16000
    result = await voice_gateway.process_voice_interaction(
        audio_data=sample_audio,
        core=mock_core,
        session_id="sess_voice_test_01",
        user_id="user_voice_01"
    )

    assert result["status"] == "success"
    assert result["transcription"] == "Commande vocale reçue par E-ZZIO"
    assert result["response_text"] == "Ordre vocal bien reçu et exécuté."
    assert len(result["audio_out"]) > 44
    assert result["session_id"] == "sess_voice_test_01"
    mock_core.think.assert_awaited_once_with(
        user_id="user_voice_01",
        message="Commande vocale reçue par E-ZZIO",
        session_id="sess_voice_test_01"
    )


@pytest.mark.asyncio
async def test_voice_empty_or_short_input(voice_gateway):
    from unittest.mock import MagicMock
    mock_core = MagicMock()

    res1 = await voice_gateway.process_voice_interaction(b"", mock_core)
    assert res1["status"] == "empty_input"

    res2 = await voice_gateway.process_voice_interaction(b"\x00", mock_core)
    assert res2["status"] == "empty_input"


@pytest.mark.asyncio
async def test_voice_security_violation_handling(voice_gateway):
    from unittest.mock import AsyncMock, MagicMock

    from core.security.guardrail import SecurityViolationError

    mock_core = MagicMock(spec=["think"])
    mock_core.think = AsyncMock(side_effect=SecurityViolationError("Tentative d'injection détectée"))

    sample_audio = b"\x00" * 16000
    res = await voice_gateway.process_voice_interaction(sample_audio, mock_core)
    assert res["status"] == "security_violation"
    assert res["response_text"] == ""
    assert res["audio_out"] == b""


@pytest.mark.asyncio
async def test_voice_core_error_handling(voice_gateway):
    from unittest.mock import AsyncMock, MagicMock

    mock_core = MagicMock(spec=["think"])
    mock_core.think = AsyncMock(side_effect=RuntimeError("Erreur interne du modèle"))

    sample_audio = b"\x00" * 16000
    res = await voice_gateway.process_voice_interaction(sample_audio, mock_core)
    assert res["status"] == "core_error"
    assert res["response_text"] == ""
    assert res["audio_out"] == b""


