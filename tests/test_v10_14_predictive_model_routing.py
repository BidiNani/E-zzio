"""
Unit & Integration Test Suite for E-ZZIO V10.14 — Model Intelligence & Predictive Routing.
"""
import pytest

from core.operations.adaptive_model_optimizer import (
    ModelResidencyState,
    TaskCategory,
    adaptive_model_optimizer,
)


def test_predictive_select_model_capability_and_residency():
    # Cold selection for simple task
    res = adaptive_model_optimizer.predictive_select_model(
        task_category=TaskCategory.SIMPLE,
        context_len=100,
        local_only=True,
    )
    assert "selected_model" in res
    assert "explanation" in res
    assert len(res["candidates"]) >= 1
    assert "POLICY > CAPABILITY" in res["explanation"]


def test_predictive_routing_code_task_preference():
    res_code = adaptive_model_optimizer.predictive_select_model(
        task_category=TaskCategory.CODE,
        context_len=1500,
        local_only=True,
    )
    assert res_code["selected_model"] in ("phi4-mini:latest", "nemotron-3-nano:4b")


def test_real_model_predictive_budgeted_call():
    res = adaptive_model_optimizer.execute_dynamic_token_budgeted_call(
        prompt="Reply OK",
        task_category=TaskCategory.SIMPLE,
    )
    assert "selected_model" in res
    assert "routing_explanation" in res
    assert "model_ms" in res
    assert res["model_ms"] > 0.0
