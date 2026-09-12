"""
tests/test_conversational_routing_policy.py — Unit test for conversational routing policy
"""
import pytest
from core.cognition.model_router import ModelRouter
from core.routing.model_registry import canonical_model_registry

def test_conversational_routing_policy_scenarios():
    router = ModelRouter()

    # 1. Chat simple (Discord / Messagerie) -> gemini-3.6-flash (off)
    r1 = router.select_engine(task_type="general", complexity_score=0.2, risk_level="low", channel="discord")
    assert r1["model"] == "gemini-3.6-flash"
    assert r1["thinking_level"] == "off"
    assert r1["role"] == "FAST_CHAT"

    # 2. Chat avec raisonnement léger -> gemini-3.6-flash (medium)
    r2 = router.select_engine(task_type="general", complexity_score=0.5, risk_level="low", channel="discord")
    assert r2["model"] == "gemini-3.6-flash"
    assert r2["thinking_level"] == "medium"
    assert r2["role"] == "STANDARD_CHAT"

    # 3. Mission moyenne -> gemini-3.8-flash (medium)
    r3 = router.select_engine(task_type="general", complexity_score=0.75, is_mission=True)
    assert r3["model"] == "gemini-3.8-flash"
    assert r3["thinking_level"] == "medium"
    assert r3["role"] == "MASTER_STRATEGIC"

    # 4. Mission complexe / Architecture -> gemini-3.8-flash (high)
    r4 = router.select_engine(task_type="general", complexity_score=0.9, is_mission=True)
    assert r4["model"] == "gemini-3.8-flash"
    assert r4["thinking_level"] == "high"
    assert r4["role"] == "MASTER_STRATEGIC"

    # 5. Coding -> gemini-3.7-flash (low)
    r5 = router.select_engine(task_type="coding", complexity_score=0.6)
    assert r5["model"] == "gemini-3.7-flash"
    assert r5["thinking_level"] == "low"
    assert r5["role"] == "CODING"

    # 6. Forensic -> gemini-3.6-flash (medium)
    r6 = router.select_engine(task_type="forensic", complexity_score=0.6)
    assert r6["model"] == "gemini-3.6-flash"
    assert r6["thinking_level"] == "medium"
    assert r6["role"] == "FORENSIC"

    # 7. Fast / Local -> minicpm5-2b-godot:latest (off)
    r7 = router.select_engine(task_type="fast_local", complexity_score=0.1)
    assert r7["model"] == "minicpm5-2b-godot:latest"
    assert r7["thinking_level"] == "off"
    assert r7["role"] == "FAST"

    # 8. Fallback GA -> gemini-2.5-flash
    rec = canonical_model_registry.get_by_role("FALLBACK")
    assert rec is not None
    assert rec.name == "gemini-2.5-flash"

if __name__ == "__main__":
    test_conversational_routing_policy_scenarios()
    print("✅ ALL ROUTING POLICY TESTS PASSED")
