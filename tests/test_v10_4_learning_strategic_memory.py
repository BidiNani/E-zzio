"""
E-ZZIO V10.4 — Critical Test Suite: Strategic Memory, Adaptive Workforce & Learning Engine.
Couvre les tests unitaires et scénarios End-to-End exigés par la spécification V10.4.
"""

import subprocess
import sys
import time

import pytest

from core.ezzio_master import EzzioMaster
from core.memory import (
    AgentReliabilityProfile,
    FailurePattern,
    MemoryCategory,
    MissionOutcome,
    ModelReliabilityProfile,
    ProviderReliabilityProfile,
    StrategicMemoryEngine,
    TeamPerformanceProfile,
    strategic_memory,
)


@pytest.fixture(autouse=True)
def setup_strategic_memory():
    strategic_memory.agent_profiles.clear()
    strategic_memory.model_profiles.clear()
    strategic_memory.provider_profiles.clear()
    strategic_memory.team_profiles.clear()
    strategic_memory.failure_patterns.clear()
    strategic_memory.set_available(True)
    yield
    strategic_memory.agent_profiles.clear()
    strategic_memory.model_profiles.clear()
    strategic_memory.provider_profiles.clear()
    strategic_memory.team_profiles.clear()
    strategic_memory.failure_patterns.clear()
    strategic_memory.set_available(True)


def test_01_scenario_a_success_learning():
    """1. Scenario A: Success Learning."""
    strategic_memory.record_mission_outcome(
        mission_id="m_001",
        outcome=MissionOutcome.SUCCESS,
        duration=2.5,
        cost=0.1,
        agents_used=["coder_worker", "qa_tester"],
        model_used="qwen3.5:9b",
        provider_used="ollama_local",
        task_type="CODING",
    )

    coder_prof = strategic_memory.agent_profiles.get("coder_worker")
    assert coder_prof is not None
    assert coder_prof.tasks_completed == 1
    assert coder_prof.success_rate == 1.0
    assert coder_prof.average_latency == 2.5

    model_prof = strategic_memory.model_profiles.get("qwen3.5:9b")
    assert model_prof is not None
    assert model_prof.tasks_completed == 1
    assert model_prof.coding_success_count == 1


def test_02_scenario_b_failure_learning_and_recovery():
    """2. Scenario B: Failure Learning & Recovery Pattern."""
    strategic_memory.record_mission_outcome(
        mission_id="m_002",
        outcome=MissionOutcome.FAILED,
        duration=5.0,
        cost=0.2,
        agents_used=["web_agent"],
        model_used="llama-3.3-70b-versatile",
        provider_used="cloud_groq",
        task_type="WEB",
        error="HTTP 504 Gateway Timeout on target URL",
        recovery_action="Fallback to SafeFetcher curl subprocess",
    )

    assert len(strategic_memory.failure_patterns) == 1
    pat = list(strategic_memory.failure_patterns.values())[0]
    assert "HTTP 504" in pat.error_signature
    assert pat.best_recovery_strategy == "Fallback to SafeFetcher curl subprocess"


def test_03_scenario_c_future_optimization_team_recommendation():
    """3. Scenario C: Future Optimization & Team Recommendation."""
    # Seed historical team performance (sample size >= 3)
    for i in range(4):
        strategic_memory.record_mission_outcome(
            mission_id=f"m_hist_{i}",
            outcome=MissionOutcome.SUCCESS,
            duration=1.2,
            cost=0.05,
            agents_used=["coder_worker", "qa_tester", "sec_guard"],
            model_used="qwen3.5:9b",
            provider_used="ollama_local",
        )

    best_team = strategic_memory.recommend_best_team("CODING")
    assert set(best_team) == {"coder_worker", "qa_tester", "sec_guard"}


def test_04_scenario_d_low_confidence_fallback():
    """4. Scenario D: Low Confidence Sample Size Fallback."""
    # Only 1 mission recorded (less than MIN_SAMPLE_SIZE_FOR_CONFIDENCE=3)
    strategic_memory.record_mission_outcome(
        mission_id="m_single",
        outcome=MissionOutcome.SUCCESS,
        duration=0.5,
        cost=0.01,
        agents_used=["image_agent"],
        model_used="gemini-3.5-flash-lite",
        provider_used="cloud_gemini",
    )

    best_team = strategic_memory.recommend_best_team("CODING")
    assert best_team == ["coder_worker", "qa_tester"]  # Default fallback


def test_05_scenario_e_learning_store_failure_fallback():
    """5. Scenario E: Learning Store Failure Graceful Fallback."""
    strategic_memory.set_available(False)  # Simulate learning memory failure

    prov = strategic_memory.recommend_best_provider("CODING", privacy_required="CLOUD_ALLOWED")
    assert prov == "cloud_groq"  # Standard default fallback

    team = strategic_memory.recommend_best_team("CODING")
    assert team == ["coder_worker", "qa_tester"]


def test_06_scenario_f_security_policy_over_adaptive_score():
    """6. Scenario F: Security Policy Over Adaptive Score (LOCAL_ONLY enforced)."""
    # Record cloud provider as 100% successful
    for i in range(5):
        strategic_memory.record_mission_outcome(
            mission_id=f"m_cloud_{i}",
            outcome=MissionOutcome.SUCCESS,
            duration=0.1,
            cost=0.0,
            agents_used=["coder_worker"],
            model_used="gemini-3.7-flash",
            provider_used="cloud_gemini",
        )

    # When LOCAL_ONLY requested -> STATIC POLICY MUST OVERRIDE ADAPTIVE RECOMMENDATION
    rec_provider = strategic_memory.recommend_best_provider("CODING", privacy_required="LOCAL_ONLY")
    assert rec_provider == "ollama_local"


def test_07_decision_explanation():
    """7. Decision Explanation Observability."""
    strategic_memory.record_mission_outcome(
        mission_id="m_exp",
        outcome=MissionOutcome.SUCCESS,
        duration=1.5,
        cost=0.05,
        agents_used=["coder_worker"],
        model_used="qwen3.5:9b",
        provider_used="ollama_local",
    )

    exp = strategic_memory.explain_decision("coder_worker", "qwen3.5:9b")
    assert exp["agent_id"] == "coder_worker"
    assert exp["model_id"] == "qwen3.5:9b"
    assert exp["agent_sample_size"] == 1
    assert "Recommended based on historical empirical data" in exp["explanation"]


def test_08_frozen_core_check():
    """8. Frozen Core remains unchanged."""
    res = subprocess.run([sys.executable, "tools/check_frozen_core.py"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "FROZEN_CORE_OK" in res.stdout
