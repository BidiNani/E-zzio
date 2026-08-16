import pytest
from core.router.intent_router import IntentRouter, IntentType

@pytest.fixture
def router():
    return IntentRouter()

def test_classify_web_search(router):
    res = router.classify("Cherche les dernières nouveautés sur Godot 4.4")
    assert res["intent"] == IntentType.WEB_SEARCH
    assert res["target_provider"] == "tavily"

def test_classify_deep_reasoning(router):
    res = router.classify("Analyse cette architecture micro-noyau et propose un refactor")
    assert res["intent"] == IntentType.DEEP_REASONING
    assert res["target_provider"] == "gemini"

def test_classify_memory_query(router):
    res = router.classify("Rappel de ce qu'on a fait sur SQLite WAL précédemment")
    assert res["intent"] == IntentType.MEMORY_QUERY
    assert res["target_provider"] == "evidence_store"

def test_classify_default_local_chat(router):
    res = router.classify("Bonjour, comment fonctionne un processeur ?")
    assert res["intent"] == IntentType.LOCAL_CHAT
    assert res["target_provider"] == "ollama"
