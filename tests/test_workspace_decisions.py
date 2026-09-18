"""Décisions workspace : next-action, source VoI, internal-first, feedback,
stall, plan source (modes existants), gaps."""
import pytest

from core.capabilities.research_fabric import Breadth, SearchIntent
from core.capabilities.workspace_decisions import (
    DecisionState,
    NextAction,
    SourceCandidate,
    StallVerdict,
    assess_stall,
    best_next_action,
    best_source_next,
    feedback_to_signal,
    gap_report,
    internal_first_order,
    source_plan,
)


def test_best_next_action_priority():
    assert best_next_action(DecisionState(blocked_on_policy=True))[0] == NextAction.ESCALATE
    assert best_next_action(DecisionState(risk_high=True))[0] == NextAction.ESCALATE
    assert best_next_action(DecisionState(cancel_requested=True))[0] == NextAction.CANCEL
    assert best_next_action(DecisionState(ambiguous=True))[0] == NextAction.ASK
    assert best_next_action(DecisionState(needs_observation=True))[0] == NextAction.MEASURE
    assert best_next_action(DecisionState(needs_specialist=True))[0] == NextAction.DELEGATE
    assert best_next_action(DecisionState(needs_external_info=True))[0] == NextAction.SEARCH
    assert best_next_action(DecisionState(waiting_on="agent"))[0] == NextAction.WAIT
    assert best_next_action(DecisionState(has_answer=True))[0] == NextAction.ANSWER
    assert best_next_action(DecisionState())[0] == NextAction.ASK


def test_best_source_value_per_cost():
    cands = [
        SourceCandidate("officiel", expected_value=9.0, cost=3.0),
        SourceCandidate("cher", expected_value=9.0, cost=9.0),
        SourceCandidate("couvert", expected_value=10.0, cost=1.0, already_covered=True),
    ]
    assert best_source_next(cands) == "officiel"  # 3.0 > 1.0, couvert exclu
    assert best_source_next([]) is None


def test_internal_first():
    assert internal_first_order(True, False) == ["internal"]
    assert internal_first_order(True, True) == ["internal", "external"]
    assert internal_first_order(False, True) == ["external"]


def test_feedback_to_evolution_signal():
    s = feedback_to_signal("C'est faux, recommence", task_id="T1", model="m")
    assert s is not None and s["signal_id"] == "feedback:answer_incorrect"
    assert s["task_id"] == "T1"
    assert feedback_to_signal("super, merci !") is None


def test_assess_stall_honest():
    assert assess_stall("RUNNING", None, 60) == StallVerdict.UNKNOWN
    assert assess_stall("RUNNING", 10.0, 60) == StallVerdict.RUNNING
    assert assess_stall("RUNNING", 600.0, 60) == StallVerdict.STALLED
    assert assess_stall("RUNNING", 600.0, 60, waiting_label="quota") == StallVerdict.WAITING
    assert assess_stall("SUCCEEDED", 9999.0, 60) == StallVerdict.RUNNING


def test_source_plan_uses_existing_modes():
    p = source_plan(SearchIntent.NEWS, Breadth.QUICK)
    assert p["mode"] == "fast" and p["budget"]["max_providers"] == 1
    pmax = source_plan(SearchIntent.RESEARCH, Breadth.MAX)
    assert pmax["budget"]["max_results"] == 10  # MAX borné, pas illimité


def test_gap_report_structure():
    g = gap_report(["a"], ["b"], ["c"], ["d"])
    assert g == {"known": ["a"], "unknown": ["b"], "conflicted": ["c"],
                 "to_verify": ["d"]}
