import pytest

from core.router.intent_router import IntentRouter, IntentType


@pytest.fixture
def router():
    return IntentRouter()


def test_classify_code_execution(router):
    res = router.classify("Exécute le script python pour lancer le serveur")
    assert res["intent"] == IntentType.CODE_EXECUTION
    assert res["target_provider"] == "system_executor"
    assert res["confidence"] >= 0.8


def test_classify_voice_action(router):
    res = router.classify("Active le micro et écoute ma voix")
    assert res["intent"] == IntentType.VOICE_ACTION
    assert res["target_provider"] == "voice_gateway"
    assert res["confidence"] >= 0.9


def test_classify_creative_synthesis(router):
    res = router.classify("Raconte une histoire sur un robot autonome")
    assert res["intent"] == IntentType.CREATIVE_SYNTHESIS
    assert res["target_provider"] == "gemini"


def test_classify_code_block(router):
    query = "Regarde ce code :\n```python\nprint('hello')\n```\net compile-le"
    res = router.classify(query)
    assert res["intent"] == IntentType.CODE_EXECUTION
