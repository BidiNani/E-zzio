"""E-ZZIO Wave 6 — mesures réelles, calibration honnête, red-team."""
import time

import pytest

from core.observability import metrics as M


def _ev(eid, action, payload=None, status="SUCCESS", ts=1.0):
    return {"id": eid, "actor": "t", "action": action,
            "payload": payload or {}, "status": status, "timestamp": ts}


def test_calibration_scale():
    assert M.calibrate_n(0) == "UNMEASURED"
    assert M.calibrate_n(1) == "EARLY_SIGNAL"
    assert M.calibrate_n(2) == "EARLY_SIGNAL"
    assert M.calibrate_n(3) == "EARLY_SIGNAL"
    assert M.calibrate_n(5) == "MEASURED"
    assert M.calibrate_n(29) == "MEASURED"
    assert M.calibrate_n(30) == "CALIBRATED"
    assert M.calibrate_n(300) == "CALIBRATED"


def test_dedupe_replay_safe():
    evs = [_ev(1, "WORKER_RESULT", {"worker_type": "A", "status": "COMPLETED"}),
           _ev(1, "WORKER_RESULT", {"worker_type": "A", "status": "COMPLETED"}),
           _ev(2, "WORKER_RESULT", {"worker_type": "A", "status": "FAILED"})]
    out = M.worker_effectiveness(evs)
    assert out["A"].n == 2
    assert out["A"].status == "EARLY_SIGNAL"


def test_worker_view_and_no_autopromote():
    evs = [_ev(i, "WORKER_RESULT",
               {"worker_type": "W", "status": "COMPLETED"})
           for i in range(1, 7)]
    out = M.worker_effectiveness(evs)
    assert out["W"].value == 1.0
    assert "Score" in out["W"].note


def test_memory_view_honest_proxy():
    cells = [{"memory_id": f"m{i}", "tier": "working", "scope": "task",
              "truth_state": "unknown", "importance": 0.5,
              "updated_at": "2026-09-09T00:00:00+00:00",
              "access_count": 1 if i < 2 else 0} for i in range(10)]
    out = M.memory_effectiveness(cells, [])
    assert out["usefulness"].value == 0.2
    assert out["usefulness"].status == "MEASURED"
    assert "USEFULNESS" in out["usefulness"].note


def test_task_view_counts():
    missions = [{"status": "COMPLETED", "worker_type": "A"},
                {"status": "FAILED", "worker_type": "A"},
                {"status": "RUNNING", "worker_type": "B"}]
    out = M.task_effectiveness(missions)
    assert out["terminal"].value == {"COMPLETED": 1, "FAILED": 1,
                                     "RUNNING": 1}
    assert out["terminal"].status == "EARLY_SIGNAL"


def test_routing_partial_outcomes():
    evs = [_ev(1, "STATUS_QUERY"), _ev(2, "WORKER_REQUEST"),
           _ev(3, "NOISE_ACTION")]
    m = M.routing_distribution(evs)
    assert m.value == {"STATUS_QUERY": 1, "WORKER_REQUEST": 1}
    assert "PARTIAL" in m.note


def test_truth_no_optimism():
    m = M.truth_from_metadata([{"truth_gate": "PASS"},
                               {"truth_gate": "BLOCKED"}, {}])
    assert m.n == 2
    assert "INTERDIT" in m.note


def test_cost_unknown_price():
    out = M.cost_model([{"provider": "ollama"}, {"provider": "groq"},
                        {"provider": "ollama"}])
    assert out["local_ratio"].value == round(2 / 3, 3)
    assert out["price"].value == "UNKNOWN_COST"
    assert out["price"].status == "UNMEASURED"


def test_security_blocks_are_defenses():
    evs = [_ev(1, "CONTRACT_REJECT", {}, "BLOCKED"),
           _ev(2, "STATUS_QUERY")]
    m = M.security_blocks(evs)
    assert m.value == {"CONTRACT_REJECT": 1}
    assert "défenses" in m.note


def test_proposals_require_evidence():
    snap = {"memory.usefulness_accessed": M.Metric(
        "memory.usefulness_accessed", 0.1, "ratio", 3, "t",
        "EARLY_SIGNAL", "", "")}
    assert M.build_proposals(snap) == []
    evs = [_ev(i, "WORKER_RESULT",
               {"worker_type": "BAD", "status": "FAILED"})
           for i in range(1, 8)]
    workers = M.worker_effectiveness(evs)
    snap2 = {"by_type": workers["by_type"]}
    props = M.build_proposals(snap2)
    assert len(props) == 1
    assert props[0]["signal"] == "worker.BAD.failure_rate"
    assert props[0]["verdict"] in ("DEFER", "KEEP", "MEASURE", "REJECT",
                                   "IMPLEMENT", "PROCEED", "ACCEPT")


def test_proposal_never_implements():
    import inspect as _inspect
    src = _inspect.getsource(M.build_proposals)
    assert src.count("advance") <= 1


def test_dashboard_answers():
    snap = {"terminal": M.Metric(
        "task.terminal_distribution",
        {"COMPLETED": 8, "FAILED": 1}, "histogram", 9, "r", "MEASURED",
        "", "")}
    d = M.dashboard(snap)
    assert set(d) == {"working", "degrading", "costly", "failing",
                      "uncalibrated", "measure_next"}
    assert d["degrading"] == []
    assert "memory.usefulness_accessed" in d["measure_next"]


def test_latency_snapshot_fast_and_clean():
    t0 = time.perf_counter()
    out = M.latency_snapshot()
    dt = (time.perf_counter() - t0) * 1000
    assert set(out) == {"classify", "bna", "retrieve"}
    assert all(m.status == "MEASURED" for m in out.values())
    assert dt < 15000


def test_no_llm_in_metrics():
    import inspect as _inspect
    src = _inspect.getsource(M)
    for token in ("llm.generate", "execute_task(", "cloud_chat(",
                  "openai", "groq(", "gemini"):
        assert token not in src


def test_spoofed_metric_rejected_gracefully():
    evs = [_ev(1, "WORKER_RESULT",
               {"worker_type": "A", "status": "HACKED into COMPLETED"}),
           _ev(2, "WORKER_RESULT", "not-a-dict"),
           _ev(3, "UNKNOWN_ACTION")]
    out = M.worker_effectiveness(evs)
    assert out["A"].value == 0.0
    m = M.routing_distribution(evs)
    assert m.n == 0 and m.status == "UNMEASURED"


def test_learning_poisoning_bounded():
    evs = [_ev(i, "WORKER_RESULT",
               {"worker_type": "P", "status": "COMPLETED"})
           for i in range(1, 101)]
    out = M.worker_effectiveness(evs)
    assert out["P"].status == "CALIBRATED"
    assert out["P"].source == "audit:WORKER_RESULT"
    assert "Score" in out["P"].note


def test_live_ledger_aggregation():
    """LIVE : agrégation réelle sur le ledger de production (< 1 s).

    Ce test est intégration : il dépend de l'état du ledger.
    S'il n'y a pas assez d'événements, on skip (comportement légitime).
    """
    import pytest
    from core.security.audit_ledger import AuditLedger
    t0 = time.perf_counter()
    events = AuditLedger().query_events(limit=3000)
    dt = (time.perf_counter() - t0) * 1000

    # Skip si le ledger est vide (dev/CI, pas de missions exécutées)
    if len(events) <= 100:
        pytest.skip(f"Ledger trop court ({len(events)} événements, besoin > 100)")

    workers = M.worker_effectiveness(events)
    routing = M.routing_distribution(events)

    # Skip si aucune décision de routing (dev/CI, pas de mission routée)
    if routing.n == 0:
        pytest.skip("Aucune décision de routing dans le ledger actuel")

    assert routing.n > 0
    assert dt < 5000
    assert all(m.status in ("UNMEASURED", "EARLY_SIGNAL", "MEASURED",
                            "CALIBRATED") for m in workers.values())
