import asyncio
import sys
from unittest.mock import MagicMock, patch

import pytest

from core.voice.voice_gateway import VoiceGateway, VoiceState


def test_voice_hardware_enumeration_and_status():
    gw = VoiceGateway()
    devices = gw.enumerate_devices()
    assert isinstance(devices, list)
    status = gw.get_status()
    assert "hardware_available" in status
    assert "sample_rate" in status
    assert status["sample_rate"] == 16000

@pytest.mark.asyncio
async def test_voice_hardware_unavailable_fail_closed():
    gw = VoiceGateway()
    gw._hardware_available = False

    with pytest.raises(RuntimeError) as exc_info:
        await gw.capture_audio()
    assert "VOICE_HARDWARE_ENVIRONMENT_LIMITED" in str(exc_info.value)

@pytest.mark.asyncio
async def test_voice_hardware_mocked_capture():
    mock_sd = MagicMock()
    mock_sd.rec.return_value = MagicMock(tobytes=lambda: bytes(32000))

    with patch.dict(sys.modules, {"sounddevice": mock_sd}):
        gw = VoiceGateway()
        gw._hardware_available = True
        audio_captured = await gw.capture_audio(duration_sec=1.0)
        assert len(audio_captured) == 32000
