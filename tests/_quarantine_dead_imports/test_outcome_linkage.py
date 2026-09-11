"""E-ZZIO Wave 6.5 — chaînage décision/exécution/outcome, anti-corrélation."""
import pytest

from core.observability import metrics as M


def _ev(eid, action, payload=None, status="SUCCESS"):
    return {"id": eid, "actor": "t", "action": action,
            "payload": payload or {}, "status": status, "timestamp": 1.0}


def test_outcome_unknown_never_success():
    with pytest.raises(ValueError):
        M.Outcome(outcome_id="x", state="UNKNOWN",
                  success_state="SUCCESS").ensure_valid()
    M.Outcome(outcome_id="x", state="SUCCESS",
              success_state="SUCCESS").ensure_valid()


def test_build_outcome_matrix():
    o = M.build_outcome("DELEGATE", "fleet-run", "COMPLETED")
    assert (o.state, o.link) == ("SUCCESS", "ASSOCIATED")
    o = M.build_outcome("ANSWER", "llm", "COMPLETED",
                        truth_verdict="BLOCKED")
    assert o.state == "PARTIAL" and o.truth_outcome == "TRUTH_FAILURE"
    o = M.build_outcome("ANSWER", "llm", "COMPLETED",
                        truth_verdict="PASS_NON_FACTUAL")
    assert o.truth_outcome == "TRUTH_OK"
    o = M.build_outcome("", "", "COMPLETED")
    assert (o.state, o.link) == ("NOT_MEASURED", "UNKNOWN")
    o = M.build_outcome("DELEGATE", "run", "COMPLETED",
                        experiment_id="exp_x_1234abcd")
    assert o.link == "CAUSALLY_SUPPORTED"


def test_linkage_gaps_closed_chain():
    evs = [_ev(1, "WORKER_REQUEST", {"request_id": "r1"}),
           _ev(2, "WORKER_RESULT",
               {"request_id": "r1", "status": "COMPLETED"}),
           _ev(3, "CANCEL_REQUEST",
               {"mission_id": "m1", "outcome": "EXECUTED"})]
    gaps = M.linkage_gaps(evs)
    assert gaps == {"decision_without_execution": 0,
                    "execution_without_decision": 0,
                    "result_without_execution": 0,
                    "request_without_result": 0}


def test_linkage_gaps_open_chain():
    evs = [_ev(1, "WORKER_REQUEST", {"request_id": "r9"}),
           _ev(2, "STATUS_QUERY", {"mission_id": "m9"})]
    gaps = M.linkage_gaps(evs)
    assert gaps["request_without_result"] == 1
    assert gaps["decision_without_execution"] == 2


def test_research_marginal_gain_and_low():
    rounds = [{"source": "tavily", "n_origins": 2, "n_claims": 3},
              {"source": "ddg", "n_origins": 2, "n_claims": 3},
              {"source": "x", "n_origins": 3, "n_claims": 3}]
    out = M.research_marginal(rounds)
    assert out["rounds"][0]["marginal"] == "GAIN"
    assert out["rounds"][1]["marginal"] == "LOW_MARGINAL_VALUE"
    assert out["rounds"][2]["marginal"] == "GAIN"
    assert out["low_value_rounds"] == 1


def test_over_signals_insufficient_by_default():
    out = M.over_signals({})
    assert out["over_memory"].value == "INSUFFICIENT_DATA"
    snap = {"memory.usefulness_accessed": M.Metric(
        "memory.usefulness_accessed", 0.0, "ratio", 8, "t", "MEASURED",
        "", "")}
    out = M.over_signals(snap)
    assert out["over_memory"].value == "MEMORY_OVER_RETRIEVAL"


def test_experiment_id_and_comparison():
    eid = M.new_experiment_id("code_fix")
    assert eid.startswith("exp_code_fix_")
    with pytest.raises(ValueError):
        M.new_experiment_id("BAD CLASS!")
    a = {"task_class": "qa", "constraints": "c", "evaluation": "e",
         "verification": "v"}
    assert M.validate_comparison(a, dict(a))[0] == "COMPARABLE"
    b = dict(a, verification="other")
    status, reasons = M.validate_comparison(a, b)
    assert status == "NOT_COMPARABLE" and reasons == ["verification differe"]


def test_false_success_detection():
    evs = [_ev(1, "WORKER_REQUEST", {"request_id": "r1"}),
           _ev(2, "WORKER_RESULT",
               {"request_id": "r1", "status": "COMPLETED",
                "worker_id": "CODER_WORKER", "artifacts": []}),
           _ev(3, "WORKER_REQUEST", {"request_id": "r2"})]
    findings = M.false_success_scan(evs, [])
    assert any("sans artefact" in f for f in findings)
    assert any("sans resultat" in f for f in findings)
    findings = M.false_success_scan(
        [], [{"mission_id": "m", "status": "COMPLETED",
              "child_failed": True}])
    assert any("enfant FAILED" in f for f in findings)


def test_event_replay_no_double_count():
    evs = [_ev(5, "CANCEL_REQUEST", {"mission_id": "m",
                                    "outcome": "EXECUTED"}),
           _ev(5, "CANCEL_REQUEST", {"mission_id": "m",
                                    "outcome": "EXECUTED"})]
    assert M.linkage_gaps(evs)["decision_without_execution"] == 0


def test_metrics_module_has_no_write_path():
    import inspect as _inspect
    src = _inspect.getsource(M)
    for token in ("record_event(", "INSERT INTO", "UPDATE ",
                  "DELETE FROM", "advance("):
        assert token not in src.replace(
            "jamais d'advance() ici", "").replace(
            "PROPOSE seul : jamais d'advance() ici.", "")


def test_live_chain_reconstruction():
    """LIVE : reconstruire une chaîne réelle REQUEST→RESULT du ledger."""
    from core.security.audit_ledger import AuditLedger
    events = AuditLedger().query_events(limit=3000)
    by_req = {}
    for e in events:
        p = e.get("payload", {}) if isinstance(
            e.get("payload"), dict) else {}
        key = str(p.get("request_id", "") or "")
        if key:
            by_req.setdefault(key, []).append(e.get("action"))
    closed = [k for k, acts in by_req.items()
              if "WORKER_REQUEST" in acts and "WORKER_RESULT" in acts]
    assert closed, "aucune chaîne fermée dans le ledger"
    gaps = M.linkage_gaps(events)
    assert isinstance(gaps["request_without_result"], int)
    research = [e for e in events if e.get("action") == "RESEARCH_OUTCOME"]
    for e in research[:5]:
        p = e.get("payload", {})
        assert "claims" in p and "stop_reason" in p


@pytest.mark.asyncio
async def test_research_outcome_emitted():
    """Lien SEARCH : audit RESEARCH_OUTCOME avec claims/rounds/stop_reason."""
    import core.ezzio_master as _m
    import core.research_router as _rr
    from core.ezzio_master import EzzioMaster
    from core.agent.coder_federation import CoderModelFederationRouter

    async def fake_research(query):
        return {"answer": "X vaut 10.", "status": "COMPLETE",
                "intent": "fact", "breadth": "quick",
                "independent_origins": 2,
                "claims": [{"id": "c0"}, {"id": "c1"}],
                "rounds": [{"source": "tavily", "status": "OK",
                            "n_claims": 2, "n_origins": 2},
                           {"source": "ddg", "status": "OK",
                            "n_claims": 2, "n_origins": 2}],
                "confidence": "high", "quality": "ok",
                "gate_verdict": "PASS", "latency_ms": 100,
                "mode": "ADAPTIVE", "stop_reason": "NO_MARGINAL_GAIN",
                "provider_calls": 2}

    async def fake_gate(text, claims=None):
        return "PASS"

    recorded = []
    _orig_research = _rr.run_adaptive_research
    _orig_audit = _m._audit_command
    _rr.run_adaptive_research = fake_research
    _m._audit_command = lambda a, p, s="SUCCESS": recorded.append(
        (a, p, s))
    try:
        router = CoderModelFederationRouter(providers={})
        master = EzzioMaster(federation_router=router)
        res = await master.execute_intent(
            "Quelle est la dernière version de Python ?", channel="web")
        assert res["routing_decision"]["action"] == "SEARCH"
        found = [p for a, p, s in recorded if a == "RESEARCH_OUTCOME"]
        assert found, "RESEARCH_OUTCOME non émis"
        assert found[0]["claims"] == 2
        assert found[0]["stop_reason"] == "NO_MARGINAL_GAIN"
        marg = M.research_marginal(found[0]["rounds"])
        assert marg["low_value_rounds"] == 1
    finally:
        _rr.run_adaptive_research = _orig_research
        _m._audit_command = _orig_audit
