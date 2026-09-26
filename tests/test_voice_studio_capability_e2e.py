"""
E-ZZIO Core V9.2 — VoiceStudio Capability Adapter E2E Test Suite (Track C).
Verifies:
1. Default disabled state (voice_enabled=False).
2. Fail-closed degradation when local VoiceStudio service is offline.
3. Audio STT/TTS result structure and CPU-only PocketTTS engine contract.
"""
import pytest

from core.capabilities.voice_studio import VoiceCapabilityResult, VoiceStudioAdapter
from core.security.audit_ledger import AuditLedger


@pytest.mark.asyncio
async def test_voicestudio_disabled_by_default(tmp_path):
    ledger = AuditLedger(db_path=str(tmp_path / "audit_vs.db"))
    adapter = VoiceStudioAdapter(audit_ledger=ledger)

    assert adapter.enabled is False
    assert adapter.engine == "pocket_tts"

    health = await adapter.check_health()
    assert health["status"] == "DISABLED"
    assert health["available"] is False

    stt_res = await adapter.transcribe(b"fake_pcm_audio")
    assert isinstance(stt_res, VoiceCapabilityResult)
    assert stt_res.status == "UNAVAILABLE"
    assert "disabled" in str(stt_res.error)

    tts_res = await adapter.synthesize("Bonjour E-ZZIO")
    assert isinstance(tts_res, VoiceCapabilityResult)
    assert tts_res.status == "UNAVAILABLE"
    assert "disabled" in str(tts_res.error)


@pytest.mark.asyncio
async def test_voicestudio_offline_service_fail_closed(tmp_path):
    ledger = AuditLedger(db_path=str(tmp_path / "audit_vs_offline.db"))
    adapter = VoiceStudioAdapter(
        base_url="http://127.0.0.1:39999",  # Nonexistent local port
        enabled=True,
        engine="pocket_tts",
        audit_ledger=ledger,
    )

    health = await adapter.check_health()
    assert health["available"] is False
    assert health["status"] == "UNAVAILABLE"

    stt_res = await adapter.transcribe(b"dummy_pcm_audio_data")
    assert stt_res.status == "UNAVAILABLE"
    assert "unresponsive" in str(stt_res.error) or "connection refused" in str(stt_res.error).lower()

    tts_res = await adapter.synthesize("Test vocal PocketTTS")
    assert tts_res.status == "UNAVAILABLE"
    assert "unresponsive" in str(tts_res.error) or "connection refused" in str(tts_res.error).lower()


@pytest.mark.asyncio
async def test_voicestudio_result_structure_contract():
    res = VoiceCapabilityResult(
        action="TTS",
        status="SUCCESS",
        text="Bonjour BidiNani",
        audio_data=b"RIFF_WAV_BYTES_DATA",
        duration_sec=1.5,
        engine="pocket_tts",
    ).to_dict()

    assert res["action"] == "TTS"
    assert res["status"] == "SUCCESS"
    assert res["has_audio"] is True
    assert res["duration_sec"] == 1.5
    assert res["engine"] == "pocket_tts"
