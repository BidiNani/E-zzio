import pytest
from runtime.cognition.loop import CognitiveLoop
from runtime.cognition.state import CognitiveState

def test_cognitive_loop_weak_information():
    """Test 2 : Une information faible (importance=0.1) ne déclenche aucune action."""
    loop = CognitiveLoop()
    result = loop.run_once({"importance": 0.1, "category": "general"})

    assert result["state"] == "IDLE"
    assert len(result["plans"]) == 1
    assert result["plans"][0]["action"] == "IGNORE"

def test_cognitive_loop_strong_information(tmp_path):
    """Test 3 : Une information forte (importance=0.9) est consolidée."""
    from runtime.cognition import EzzioBrain
    from runtime.knowledge.store import KnowledgeStore

    brain = EzzioBrain(long_term_knowledge=KnowledgeStore(str(tmp_path / "loop_ezzio.db")))
    loop = CognitiveLoop(brain=brain)
    
    result = loop.run_once({"importance": 0.9, "category": "tech"})

    assert result["state"] == "IDLE"
    actions = [p["action"] for p in result["plans"]]
    assert "STORE_KNOWLEDGE" in actions
    
    # Vérifie l'apprentissage effectif via le mot-clé garanti 'audit'
    facts = brain.long_term.search_knowledge_by_keywords(["audit"])
    assert len(facts) > 0

def test_cognitive_loop_error_handling():
    """Test 4 : Une erreur d'action retourne proprement vers IDLE / ERROR state."""
    loop = CognitiveLoop()
    loop.observe = lambda raw=None: (_ for _ in "").throw(RuntimeError("Simulated system fault"))
    
    result = loop.run_once({"importance": 0.9})
    assert result["state"] == "ERROR"
    assert "Simulated system fault" in result["error"]

def test_cognitive_loop_full_cycle_events():
    """Test 1 : Cycle complet traçable via l'Event Bus."""
    loop = CognitiveLoop()
    loop.run_once({"importance": 0.8, "category": "news_feed"})

    history = loop.event_bus.get_history()
    event_types = [e.event_type for e in history]

    assert "OBSERVATION_RECEIVED" in event_types
    assert "ANALYSIS_COMPLETED" in event_types
    assert "REASONING_DECIDED" in event_types
    assert "ACTION_COMPLETED" in event_types
    assert "LEARNING_FEEDBACK_PROCESSED" in event_types
