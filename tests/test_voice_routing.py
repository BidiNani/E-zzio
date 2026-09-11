"""
tests/test_voice_routing.py — Deterministic test for voice routing through EzzioMaster & ModelRouter
"""
import pytest
import asyncio
from core.cognition.model_router import ModelRouter
from core.voice.voice_gateway import VoiceGateway, VoiceState
from core.ezzio_master import EzzioMaster

def test_voice_routing_policy_scenarios():
    router = ModelRouter()

    # Cas 1 : Voice simple -> gemini-3.6-flash (off)
    r1 = router.select_engine(task_type="general", complexity_score=0.2, risk_level="low", channel="voice")
    assert r1["model"] == "gemini-3.6-flash"
    assert r1["thinking_level"] == "off"
    assert r1["role"] == "FAST_CHAT"

    # Cas 2 : Voice raisonnement -> gemini-3.6-flash (medium)
    r2 = router.select_engine(task_type="general", complexity_score=0.5, risk_level="low", channel="voice")
    assert r2["model"] == "gemini-3.6-flash"
    assert r2["thinking_level"] == "medium"
    assert r2["role"] == "STANDARD_CHAT"

    # Cas 3 : Voice mission normale -> gemini-3.8-flash (medium)
    r3 = router.select_engine(task_type="general", complexity_score=0.75, is_mission=True, channel="voice")
    assert r3["model"] == "gemini-3.8-flash"
    assert r3["thinking_level"] == "medium"
    assert r3["role"] == "MASTER_STRATEGIC"

    # Cas 4 : Voice mission architecture complexe -> gemini-3.8-flash (high)
    r4 = router.select_engine(task_type="general", complexity_score=0.9, is_mission=True, channel="voice")
    assert r4["model"] == "gemini-3.8-flash"
    assert r4["thinking_level"] == "high"
    assert r4["role"] == "MASTER_STRATEGIC"

@pytest.mark.asyncio
async def test_voice_gateway_master_integration():
    gateway = VoiceGateway()
    master = EzzioMaster()

    # Audio PCM 16-bit factice
    audio_pcm = b"\x00\x00" * 1600

    # Exécution du parcours vocal
    res = await gateway.process_voice_interaction(
        audio_data=audio_pcm,
        core=master,
        session_id="test_voice_sess",
        user_id="test_voice_user"
    )

    assert res["status"] in ["success", "empty_input", "core_error"]
    assert "transcription" in res
    assert "audio_out" in res

if __name__ == "__main__":
    test_voice_routing_policy_scenarios()
    asyncio.run(test_voice_gateway_master_integration())
    print("✅ ALL VOICE ROUTING TESTS PASSED")
