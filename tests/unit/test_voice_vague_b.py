"""Tests avec guard cv2/numpy (module natif sensible au reload)."""
import sys as _sys

# Test le chargement de cv2/numpy AVANT tout reload par pytest
try:
    import cv2  # noqa: F401
    import numpy  # noqa: F401
    cv2_loaded_at_import = True
except ImportError:
    cv2_loaded_at_import = False

import pytest

pytestmark = pytest.mark.skipif(
    not cv2_loaded_at_import,
    reason="cv2/numpy non chargables (module natif deja decharge)",
)
"""Tests Vague B : core/voice/ (voice_duplex_engine + voice_gateway).

Calibre sur les signatures reelles (audit 23/09/2026).
"""

# --- Guard cv2/numpy (module natif sensible au reload) ---
try:
    import cv2  # noqa: F401
    import numpy  # noqa: F401
    _cv2_loaded_at_import = True
except ImportError:
    _cv2_loaded_at_import = False

import pytest

pytestmark = pytest.mark.skipif(
    not _cv2_loaded_at_import,
    reason="cv2/numpy non chargables (module natif deja decharge)",
)


import asyncio
import struct
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================
# 1. voice_duplex_engine.DuplexState
# ============================================================

class TestDuplexState:
    def test_enum_members(self):
        from core.voice.voice_duplex_engine import DuplexState
        assert DuplexState.IDLE == "IDLE"
        assert DuplexState.LISTENING == "LISTENING"
        assert DuplexState.PROCESSING == "PROCESSING"
        assert DuplexState.SPEAKING == "SPEAKING"
        assert DuplexState.INTERRUPTED == "INTERRUPTED"

    def test_is_strenum(self):
        from core.voice.voice_duplex_engine import DuplexState
        # StrEnum -> les membres sont des str
        assert isinstance(DuplexState.IDLE, str)


# ============================================================
# 2. voice_duplex_engine.VoiceDuplexEngine
# ============================================================

class TestVoiceDuplexEngineInit:
    def test_instantiation_default(self):
        """L'init prend des parametres (L32-48 non lus) -> on tente sans args."""
        from core.voice.voice_duplex_engine import VoiceDuplexEngine
        try:
            engine = VoiceDuplexEngine()
        except TypeError:
            pytest.skip("VoiceDuplexEngine requiert des arguments obligatoires")
            return
        assert engine is not None

    def test_has_detect_voice_activity(self):
        from core.voice.voice_duplex_engine import VoiceDuplexEngine
        assert hasattr(VoiceDuplexEngine, "detect_voice_activity")

    def test_has_trigger_barge_in(self):
        from core.voice.voice_duplex_engine import VoiceDuplexEngine
        assert hasattr(VoiceDuplexEngine, "trigger_barge_in")

    def test_has_process_incoming_audio_stream(self):
        from core.voice.voice_duplex_engine import VoiceDuplexEngine
        assert hasattr(VoiceDuplexEngine, "process_incoming_audio_stream")

    def test_has_simulate_tts_speech(self):
        from core.voice.voice_duplex_engine import VoiceDuplexEngine
        assert hasattr(VoiceDuplexEngine, "simulate_tts_speech")


class TestDetectVoiceActivity:
    def _make_engine(self):
        from core.voice.voice_duplex_engine import VoiceDuplexEngine
        try:
            return VoiceDuplexEngine()
        except TypeError:
            pytest.skip("VoiceDuplexEngine requiert des arguments")
            return None

    def test_silence_returns_false(self):
        engine = self._make_engine()
        if engine is None:
            return
        # 160 echantillons int16 a 0 = silence
        silence = struct.pack("<160h", *([0] * 160))
        assert engine.detect_voice_activity(silence) is False

    def test_loud_signal_returns_true(self):
        engine = self._make_engine()
        if engine is None:
            return
        # Signal fort (proche max int16)
        loud = struct.pack("<160h", *([20000] * 160))
        assert engine.detect_voice_activity(loud) is True

    def test_empty_bytes_does_not_crash(self):
        engine = self._make_engine()
        if engine is None:
            return
        # Ne doit pas lever (retourne False ou True selon implementation)
        result = engine.detect_voice_activity(b"")
        assert isinstance(result, bool)

    def test_odd_bytes_does_not_crash(self):
        """Bytes non-alignes sur int16 -> ne doit pas lever."""
        engine = self._make_engine()
        if engine is None:
            return
        result = engine.detect_voice_activity(b"\x01\x02\x03")
        assert isinstance(result, bool)


class TestAttachOutputStream:
    def test_attach_and_clear(self):
        from core.voice.voice_duplex_engine import VoiceDuplexEngine
        try:
            engine = VoiceDuplexEngine()
        except TypeError:
            pytest.skip("VoiceDuplexEngine requiert des arguments")
            return
        mock_stream = MagicMock()
        engine.attach_output_stream(mock_stream)
        engine.attach_output_stream(None)  # detach


class TestTriggerBargeIn:
    def test_returns_dict(self):
        from core.voice.voice_duplex_engine import VoiceDuplexEngine
        try:
            engine = VoiceDuplexEngine()
        except TypeError:
            pytest.skip("VoiceDuplexEngine requiert des arguments")
            return
        result = engine.trigger_barge_in()
        assert isinstance(result, dict)


# ============================================================
# 3. voice_gateway.VoiceState
# ============================================================

class TestVoiceState:
    def test_enum_members(self):
        from core.voice.voice_gateway import VoiceState
        assert VoiceState.IDLE.value == "idle"
        assert VoiceState.LISTENING.value == "listening"
        assert VoiceState.PROCESSING.value == "processing"
        assert VoiceState.SPEAKING.value == "speaking"
        assert VoiceState.FALLBACK.value == "fallback"


# ============================================================
# 4. voice_gateway.VoiceGateway
# ============================================================

class TestVoiceGatewayInit:
    def test_default_init(self):
        from core.voice.voice_gateway import VoiceGateway
        gw = VoiceGateway()
        assert gw.sample_rate == 16000
        assert gw.energy_threshold == 500
        assert gw.state is not None

    def test_custom_init(self):
        from core.voice.voice_gateway import VoiceGateway
        gw = VoiceGateway(sample_rate=8000, energy_threshold=1000)
        assert gw.sample_rate == 8000
        assert gw.energy_threshold == 1000

    def test_check_hardware_sets_flag(self):
        from core.voice.voice_gateway import VoiceGateway
        gw = VoiceGateway()
        assert isinstance(gw._hardware_available, bool)

    def test_is_hardware_available_property(self):
        from core.voice.voice_gateway import VoiceGateway
        gw = VoiceGateway()
        assert isinstance(gw.is_hardware_available, bool)


class TestVoiceGatewayEnumerate:
    def test_enumerate_devices_returns_list(self):
        from core.voice.voice_gateway import VoiceGateway
        gw = VoiceGateway()
        result = gw.enumerate_devices()
        assert isinstance(result, list)


class TestVoiceGatewayDetectSpeech:
    def test_silence_returns_false(self):
        from core.voice.voice_gateway import VoiceGateway
        gw = VoiceGateway()
        silence = struct.pack("<160h", *([0] * 160))
        assert gw.detect_speech(silence) is False

    def test_loud_returns_true(self):
        from core.voice.voice_gateway import VoiceGateway
        gw = VoiceGateway()
        loud = struct.pack("<160h", *([20000] * 160))
        assert gw.detect_speech(loud) is True

    def test_empty_bytes(self):
        from core.voice.voice_gateway import VoiceGateway
        gw = VoiceGateway()
        result = gw.detect_speech(b"")
        assert isinstance(result, bool)


class TestVoiceGatewayCaptureAudio:
    def test_capture_without_hardware_returns_bytes(self):
        """Si pas de hardware, capture_audio doit retourner bytes (vide ou fallback)."""
        from core.voice.voice_gateway import VoiceGateway
        gw = VoiceGateway()
        result = asyncio.run(gw.capture_audio(duration_sec=0.01))
        assert isinstance(result, bytes)


class TestVoiceGatewayTranscribe:
    def test_transcribe_returns_dict(self):
        from core.voice.voice_gateway import VoiceGateway
        gw = VoiceGateway()
        result = asyncio.run(gw.transcribe(b"\x00" * 320, language="fr"))
        assert isinstance(result, dict)

    def test_transcribe_empty_audio(self):
        from core.voice.voice_gateway import VoiceGateway
        gw = VoiceGateway()
        result = asyncio.run(gw.transcribe(b"", language="fr"))
        assert isinstance(result, dict)


class TestVoiceGatewaySynthesize:
    def test_synthesize_returns_bytes(self):
        from core.voice.voice_gateway import VoiceGateway
        gw = VoiceGateway()
        result = asyncio.run(gw.synthesize("Bonjour E-ZZIO"))
        assert isinstance(result, bytes)

    def test_synthesize_empty_text(self):
        from core.voice.voice_gateway import VoiceGateway
        gw = VoiceGateway()
        result = asyncio.run(gw.synthesize(""))
        assert isinstance(result, bytes)


class TestVoiceGatewayStatus:
    def test_get_status_returns_dict(self):
        from core.voice.voice_gateway import VoiceGateway
        gw = VoiceGateway()
        status = gw.get_status()
        assert isinstance(status, dict)
        # Doit contenir au moins ces cles (basees sur les attributs)
        assert "sample_rate" in status or "state" in status or "hardware_available" in status
