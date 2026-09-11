"""
Unit & Integration Test Suite for E-ZZIO V10.12 — Adaptive Model & Execution Optimization.
"""
import pytest
import time
import shutil
from pathlib import Path

from core.agent.autonomous_e2e_engine import autonomous_e2e_engine, MissionState
from core.operations.adaptive_model_optimizer import (
    adaptive_model_optimizer,
    ModelResidencyState,
)


def test_model_residency_tracking_and_warm_start():
    # Reset model state
    prof = adaptive_model_optimizer.residency_registry.get("phi4-mini:latest")
    if prof:
        prof.residency_state = ModelResidencyState.NOT_LOADED
        prof.total_calls = 0

    # Cold call
    res_cold = adaptive_model_optimizer.execute_optimized_model_call(
        prompt="Hi", model="phi4-mini:latest", max_tokens=5
    )
    assert res_cold["residency_state"] == "COLD"
    assert res_cold["model_ms"] > 0.0

    # Warm call
    res_warm = adaptive_model_optimizer.execute_optimized_model_call(
        prompt="Hi", model="phi4-mini:latest", max_tokens=5
    )
    assert res_warm["residency_state"] == "WARM"
    assert res_warm["model_ms"] > 0.0


def test_latency_aware_routing():
    # Make phi4-mini WARM
    prof = adaptive_model_optimizer.residency_registry["phi4-mini:latest"]
    prof.residency_state = ModelResidencyState.RESIDENT
    prof.last_invoked_at = time.time()

    # Request a cold model -> should route to warm phi4-mini
    selected = adaptive_model_optimizer.select_latency_aware_model("GENERIC", preferred_model="nemotron-3-nano:4b")
    assert selected == "phi4-mini:latest"


def test_parallel_independent_nodes():
    def task_1():
        time.sleep(0.01)
        return "res1"

    def task_2():
        time.sleep(0.01)
        return "res2"

    t0 = time.perf_counter()
    results = adaptive_model_optimizer.execute_parallel_nodes([task_1, task_2])
    t1 = time.perf_counter()

    duration = t1 - t0
    assert results == ["res1", "res2"]
    # Concurrent execution duration should be ~0.01s (much less than sequential 0.02s)
    assert duration < 0.018


def test_3_mission_before_after_latency_benchmark():
    test_dir = Path("state/tmp/v10_12_model_execution_test")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Benchmark M1: Simple Reasoning
        res_m1 = adaptive_model_optimizer.execute_optimized_model_call(
            prompt="Compute 2+2 in 1 word", model="phi4-mini:latest", max_tokens=5
        )
        assert res_m1["response"] != ""

        # Benchmark M2: Model + File Tool
        f_out = test_dir / "m2.json"
        f_out.parent.mkdir(parents=True, exist_ok=True)
        res_m2_model = adaptive_model_optimizer.execute_optimized_model_call(
            prompt="Summary in 3 words", model="phi4-mini:latest", max_tokens=10
        )
        f_out.write_text(res_m2_model["response"], encoding="utf-8")
        assert f_out.exists()

        # Benchmark M3: Parallel Tasks
        p_res = adaptive_model_optimizer.execute_parallel_nodes([
            lambda: adaptive_model_optimizer.execute_optimized_model_call("Word 1", max_tokens=5),
            lambda: adaptive_model_optimizer.execute_optimized_model_call("Word 2", max_tokens=5),
        ])
        assert len(p_res) == 2

    finally:
        if test_dir.exists():
            shutil.rmtree(test_dir)
