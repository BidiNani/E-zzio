"""
Unit & Integration Test Suite for E-ZZIO V10.13 — Adaptive Warm Residency & Dynamic Token Budgeting.
"""
import pytest
import time
import shutil
from pathlib import Path

from core.operations.adaptive_model_optimizer import (
    adaptive_model_optimizer,
    ModelResidencyState,
    MemoryPressureState,
    PrewarmDecision,
    TaskCategory,
)


def test_residency_states_and_memory_pressure_governance():
    # Reset state
    adaptive_model_optimizer.update_memory_pressure(MemoryPressureState.NORMAL)
    prof = adaptive_model_optimizer.residency_registry["phi4-mini:latest"]
    prof.residency_state = ModelResidencyState.NOT_LOADED

    # High confidence prewarm -> PREWARM
    dec1 = adaptive_model_optimizer.evaluate_prewarm_decision("phi4-mini:latest", confidence=0.85)
    assert dec1 == PrewarmDecision.PREWARM

    # Under High Pressure -> DEFER
    adaptive_model_optimizer.update_memory_pressure(MemoryPressureState.HIGH_PRESSURE)
    dec2 = adaptive_model_optimizer.evaluate_prewarm_decision("phi4-mini:latest", confidence=0.85)
    assert dec2 == PrewarmDecision.DEFER

    adaptive_model_optimizer.update_memory_pressure(MemoryPressureState.NORMAL)


def test_safe_eviction_under_memory_pressure():
    adaptive_model_optimizer.update_memory_pressure(MemoryPressureState.NORMAL)
    prof = adaptive_model_optimizer.residency_registry["phi4-mini:latest"]
    prof.residency_state = ModelResidencyState.RESIDENT
    prof.last_invoked_at = time.time() - 400  # Idle > 300s

    # Evict idle models not active in running mission
    evicted = adaptive_model_optimizer.evict_idle_models(active_models=["nemotron-3-nano:4b"])
    assert "phi4-mini:latest" in evicted
    assert prof.residency_state == ModelResidencyState.NOT_LOADED


def test_dynamic_token_budget_estimation():
    budget_simple = adaptive_model_optimizer.estimate_dynamic_token_budget(TaskCategory.SIMPLE, prompt_len=20)
    assert budget_simple["initial_budget"] < 35

    budget_code = adaptive_model_optimizer.estimate_dynamic_token_budget(TaskCategory.CODE, prompt_len=100, schema_required=True)
    assert budget_code["initial_budget"] > 250
    assert budget_code["max_budget"] > budget_code["initial_budget"]


def test_truncation_detection_and_adaptive_expansion_loop():
    # Test response truncated
    is_trunc = adaptive_model_optimizer.is_response_truncated("The gravity equation is F = G * m1 * m2 / r", max_tokens=10)
    assert is_trunc is True

    is_complete = adaptive_model_optimizer.is_response_truncated("Gravity is an attractive force.", max_tokens=10)
    assert is_complete is False


def test_real_model_dynamic_budgeted_call():
    res = adaptive_model_optimizer.execute_dynamic_token_budgeted_call(
        prompt="Explain gravity in 5 words.",
        task_category=TaskCategory.SIMPLE,
        model="phi4-mini:latest",
    )
    assert "response" in res
    assert res["model_ms"] > 0.0
    assert res["final_budget"] >= 15
    assert res["expansions_used"] >= 0
