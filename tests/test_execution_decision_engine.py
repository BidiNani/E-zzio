"""Tests for core/cognition/execution_decision_engine.py (Mission 21 Architectural Convergence)."""

import pytest
from core.cognition.execution_decision_engine import ExecutionDecisionEngine, ExecutionDecision


def test_execution_decision_engine_default_selection(tmp_path):
    engine = ExecutionDecisionEngine(workspace_root=str(tmp_path))
    decision = engine.evaluate_and_decide(
        task_type="coding",
        objective="Implement feature",
        require_worker=True,
    )
    assert isinstance(decision, ExecutionDecision)
    assert decision.execution_type == "WORKER"
    assert decision.target_id in ("native", "hermes", "cline", "pig")
    assert decision.score > 0
    assert decision.fallback_target_id == "native"


def test_execution_decision_engine_preferred_target(tmp_path):
    engine = ExecutionDecisionEngine(workspace_root=str(tmp_path))
    decision = engine.evaluate_and_decide(
        task_type="coding",
        preferred_target="native",
        require_worker=True,
    )
    assert decision.target_id == "native"
    assert decision.execution_type == "WORKER"


def test_execution_decision_engine_with_jev_hint(tmp_path):
    engine = ExecutionDecisionEngine(workspace_root=str(tmp_path))
    jev_hint = {"recommended_worker": "native", "confidence": 0.95}
    decision = engine.evaluate_and_decide(
        task_type="coding",
        require_worker=True,
        jev_hint=jev_hint,
    )
    assert decision.target_id == "native"
    assert "jev_hint_applied" in str(decision.candidate_scores) or decision.score > 0


def test_execution_decision_engine_model_selection(tmp_path):
    engine = ExecutionDecisionEngine(workspace_root=str(tmp_path))
    decision = engine.evaluate_and_decide(
        task_type="coding",
        require_worker=False,
        prefer_local=True,
    )
    assert decision.execution_type in ("MODEL", "WORKER")
    assert decision.target_id is not None
