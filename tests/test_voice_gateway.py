import io
import struct
import sys
import wave
from unittest.mock import AsyncMock, MagicMock, patch

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




class TestVoiceGatewayExtended:
    """Tests etendus pour couvrir les branches non testees."""

    @patch("core.voice.voice_gateway.VoiceGateway._check_hardware")
    def test_detect_speech_empty_or_short(self, mock_check):
        gw = VoiceGateway()
        assert gw.detect_speech(b"") is False
        assert gw.detect_speech(b"\x00") is False

    @patch("core.voice.voice_gateway.VoiceGateway._check_hardware")
    def test_detect_speech_exception(self, mock_check):
        gw = VoiceGateway()
        assert gw.detect_speech(b"\x00\x01\x02") is False

    @pytest.mark.asyncio
    @patch("core.voice.voice_gateway.VoiceGateway._check_hardware")
    async def test_synthesize_empty_text(self, mock_check):
        gw = VoiceGateway()
        result = await gw.synthesize("")
        assert result == b""
        assert gw.state == VoiceState.IDLE

    @pytest.mark.asyncio
    @patch("core.voice.voice_gateway.VoiceGateway._check_hardware")
    async def test_synthesize_whitespace_only(self, mock_check):
        gw = VoiceGateway()
        result = await gw.synthesize("   ")
        assert result == b""

    @pytest.mark.asyncio
    @patch("core.voice.voice_gateway.VoiceGateway._check_hardware")
    async def test_process_voice_interaction_execute_intent(self, mock_check):
        gw = VoiceGateway()
        mock_core = MagicMock(spec=["execute_intent"])
        mock_core.execute_intent = AsyncMock(return_value={"response": "Reponse via execute_intent"})

        sample_audio = b"\x00" * 16000
        res = await gw.process_voice_interaction(
            audio_data=sample_audio,
            core=mock_core,
            session_id="sess_intent",
            user_id="user_intent",
        )
        assert res["status"] == "success"
        assert res["response_text"] == "Reponse via execute_intent"
        mock_core.execute_intent.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("core.voice.voice_gateway.VoiceGateway._check_hardware")
    async def test_process_voice_interaction_core_none_fallback(self, mock_check):
        gw = VoiceGateway()
        mock_master = MagicMock()
        mock_master.execute_intent = AsyncMock(return_value={"response": "Fallback master"})

        with patch("core.ezzio_master.ezzio_master", mock_master):
            sample_audio = b"\x00" * 16000
            res = await gw.process_voice_interaction(audio_data=sample_audio, core=None)
            assert res["status"] in ("success", "core_error")


class TestVoiceGatewayFullCoverage:
    """Tests pour atteindre 100% de couverture sur voice_gateway."""

    @patch("core.voice.voice_gateway.VoiceGateway._check_hardware")
    def test_detect_speech_exception_returns_false(self, mock_check):
        gw = VoiceGateway()
        with patch("core.voice.voice_gateway.struct.unpack", side_effect=RuntimeError("boom")):
            assert gw.detect_speech(b"\x01\x02") is False

    def test_check_hardware_with_mock_sounddevice(self):
        mock_sd = MagicMock()
        mock_sd.query_devices = MagicMock(return_value=[{"name": "test"}])
        with patch.dict(sys.modules, {"sounddevice": mock_sd}):
            gw = VoiceGateway()
            assert gw._hardware_available is True

    def test_enumerate_devices_with_mock(self):
        mock_sd = MagicMock()
        mock_sd.query_devices = MagicMock(return_value=[{"name": "dev1"}, {"name": "dev2"}])
        with patch.dict(sys.modules, {"sounddevice": mock_sd}):
            gw = VoiceGateway()
            devices = gw.enumerate_devices()
            assert len(devices) == 2

    @pytest.mark.asyncio
    async def test_transcribe_with_stt_exception(self):
        gw = VoiceGateway()
        mock_core = MagicMock()

        with patch.object(gw, "transcribe", side_effect=RuntimeError("STT fail")):
            sample_audio = b"\x00" * 16000
            res = await gw.process_voice_interaction(sample_audio, mock_core)
            assert res["status"] == "stt_error"
            assert "STT fail" in res["error"]

    @pytest.mark.asyncio
    async def test_transcribe_empty_audio_returns_empty_status(self):
        gw = VoiceGateway()
        res = await gw.transcribe(b"")
        assert res["status"] == "empty"
        assert res["text"] == ""
        assert res["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_synthesize_with_wave_error(self):
        gw = VoiceGateway()
        mock_core = MagicMock(spec=["think"])
        mock_core.think = AsyncMock(return_value={"response": "Test response"})

        with patch.object(gw, "synthesize", side_effect=RuntimeError("TTS fail")):
            sample_audio = b"\x00" * 16000
            res = await gw.process_voice_interaction(sample_audio, mock_core)
            assert res["status"] == "tts_error"
            assert "TTS fail" in res["error"]

    @pytest.mark.asyncio
    async def test_capture_audio_with_mock_sounddevice(self):
        mock_sd = MagicMock()
        mock_recording = MagicMock()
        mock_recording.tobytes = MagicMock(return_value=b"\x00" * 32000)
        mock_sd.rec = MagicMock(return_value=mock_recording)
        mock_sd.wait = MagicMock()

        with patch.dict(sys.modules, {"sounddevice": mock_sd}):
            gw = VoiceGateway()
            gw._hardware_available = True
            audio = await gw.capture_audio(duration_sec=1.0)
            assert len(audio) == 32000

    @pytest.mark.asyncio
    async def test_capture_audio_exception(self):
        mock_sd = MagicMock()
        mock_sd.rec = MagicMock(side_effect=RuntimeError("hardware fail"))

        with patch.dict(sys.modules, {"sounddevice": mock_sd}):
            gw = VoiceGateway()
            gw._hardware_available = True
            with pytest.raises(RuntimeError, match="chec de capture audio"):
                await gw.capture_audio(duration_sec=1.0)


class TestVoiceGatewayFinalCoverage:
    """Tests finaux pour atteindre 100% sur voice_gateway."""

    def test_check_hardware_exception_sets_false(self):
        # Couvre L35-36 : except Exception -> _hardware_available = False
        mock_sd = MagicMock()
        mock_sd.query_devices = MagicMock(side_effect=RuntimeError("driver fail"))
        with patch.dict(sys.modules, {"sounddevice": mock_sd}):
            gw = VoiceGateway()
            assert gw._hardware_available is False

    def test_is_hardware_available_property(self):
        # Couvre L40 : property is_hardware_available (retour True)
        mock_sd = MagicMock()
        mock_sd.query_devices = MagicMock(return_value=[{"name": "test"}])
        with patch.dict(sys.modules, {"sounddevice": mock_sd}):
            gw = VoiceGateway()
            # _hardware_available = True apres _check_hardware
            assert gw.is_hardware_available is True

    def test_enumerate_devices_exception_returns_empty(self):
        # Couvre L47-49 : except Exception -> logger.debug + return []
        mock_sd = MagicMock()
        mock_sd.query_devices = MagicMock(side_effect=RuntimeError("enum fail"))
        with patch.dict(sys.modules, {"sounddevice": mock_sd}):
            gw = VoiceGateway()
            # Patch APRES construction pour eviter _check_hardware
            with patch.dict(sys.modules, {"sounddevice": mock_sd}):
                devices = gw.enumerate_devices()
                assert devices == []

    @pytest.mark.asyncio
    async def test_capture_audio_hardware_exception_during_rec(self):
        # Couvre L54 : except Exception -> RuntimeError "Echec de capture audio materielle"
        mock_sd = MagicMock()
        mock_sd.rec = MagicMock(side_effect=OSError("device busy"))
        mock_sd.wait = MagicMock()

        with patch.dict(sys.modules, {"sounddevice": mock_sd}):
            gw = VoiceGateway()
            gw._hardware_available = True
            with pytest.raises(RuntimeError, match="chec de capture audio"):
                await gw.capture_audio(duration_sec=1.0)

    @pytest.mark.asyncio
    async def test_process_voice_interaction_empty_transcription(self):
        # Couvre L159 : user_prompt vide -> status "empty_input"
        gw = VoiceGateway()
        mock_core = MagicMock()

        with patch.object(gw, "transcribe", return_value={"text": "", "status": "success"}):
            sample_audio = b"\x00" * 16000
            res = await gw.process_voice_interaction(sample_audio, mock_core)
            assert res["status"] == "empty_input"
            assert res["transcription"] == ""
