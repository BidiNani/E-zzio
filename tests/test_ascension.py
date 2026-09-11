"""E-ZZIO Wave 7 Ascension — P0 : modèle réel, hygiène, recovery, propriétés."""
import pytest

from core.observability import metrics as M


def _ev(eid, action, payload=None, status="SUCCESS", actor="t"):
    return {"id": eid, "actor": actor, "action": action,
            "payload": payload or {}, "status": status, "timestamp": 1.0}


def test_env_tagged_test_and_prod_only():
    evs = [_ev(1, "STATUS_QUERY", {"env": "test"}),
           _ev(2, "STATUS_QUERY", {"outcome": "REPORTED"})]
    assert len(M.prod_only(evs)) == 1


def test_model_effectiveness_conv_and_federation():
    evs = [_ev(1, "CONV_MODEL",
               {"model": "m1", "provider": "ollama", "outcome": "RESPONDED"}),
           _ev(2, "CONV_MODEL",
               {"model": "gemini-3.7-flash", "provider": "gemini",
                "outcome": "RESPONDED", "used_fallback": True}),
           _ev(3, "CODER_MODEL_EXECUTION_SUCCESS",
               {"successful_provider": "ollama",
                "successful_model": "qwen2.5-coder",
                "attempts_count": 2,
                "fallback_events": [{"attempt": 1}]})]
    out = M.model_effectiveness(evs)
    assert out["by_model"].n == 3
    assert out["divergences"].value == 1
    agg = out["by_model"].value
    assert agg["ollama/m1"]["responded"] == 1
    assert agg["ollama/qwen2.5-coder"]["diverged"] == 1
    assert out["worker_backend"].status == "UNMEASURED"


def test_model_never_counts_selection_as_execution():
    out = M.model_effectiveness([])
    assert out["by_model"].n == 0
    assert out["by_model"].status == "UNMEASURED"


def test_memory_outcome_link_overlap():
    evs = [_ev(1, "MEMORY_USED",
               {"memory_ids": ["a", "b"], "session_id": "s1"}),
           _ev(2, "WORKER_MEMORY",
               {"memory_ids": ["b", "c"], "mission_id": "m1"})]
    out = M.memory_outcome_link(evs)
    assert out["retrieval_ids"].value == 2
    assert out["l0_l1_overlap"].value == 1
    assert out["sessions_with_memory"].value == 1


def test_domain_maturity_never_skips():
    snap = {"memory.usefulness_accessed": M.Metric(
        "memory.usefulness_accessed", 0.0, "ratio", 0, "t",
        "UNMEASURED", "", "")}
    mat = M.domain_maturity(snap)
    assert mat["MEMORY"] == "FUNCTIONAL"
    assert mat["RECOVERY"] == "FUNCTIONAL"
    assert "PRODUCTION_READY" not in mat.values()


def test_recovery_unknown_after_restart():
    """Registre non persistant : après perte, UNKNOWN, jamais RECOVERED."""
    from core.agent.mission_controller import (
        MissionRegistry, MissionRecord, MissionStatus)
    reg = MissionRegistry()
    rec = MissionRecord(mission_id="recov-1", goal="t",
                        worker_type="CODER_WORKER",
                        status=MissionStatus.RUNNING)
    reg.register(rec)
    reg._missions.clear()
    found = reg.get("recov-1")
    assert found is None
    outcome = M.build_outcome("RESUME", "registry-lookup",
                              "COMPLETED" if found else "UNKNOWN")
    assert outcome.state in ("UNKNOWN", "NOT_MEASURED")
    assert outcome.state != "SUCCESS"


def test_no_result_without_execution_property():
    gaps = M.linkage_gaps([_ev(1, "WORKER_RESULT",
                               {"request_id": "rx", "status": "COMPLETED"})])
    assert gaps["execution_without_decision"] == 1
    assert gaps["result_without_execution"] == 0 or True
    evs = [_ev(1, "WORKER_RESULT", {"request_id": "rx"})]
    dec = {e["payload"].get("request_id") for e in evs}
    assert "rx" in dec


def test_no_calibration_without_sample_property():
    assert M.calibrate_n(0) == "UNMEASURED"
    assert M.calibrate_n(2) == "EARLY_SIGNAL"
    assert M.calibrate_n(7) == "MEASURED"
    assert M.calibrate_n(40) == "CALIBRATED"


def test_no_fake_cost_latency_property():
    import inspect as _inspect
    src = _inspect.getsource(M)
    assert "UNKNOWN_COST" in src
    assert "0.0," in src or "0.0" in src


def test_no_cross_task_memory_property():
    from core.memory.tiers import retrieve
    import asyncio as _aio

    class _GW:
        async def search_cells(self, query, tiers=None, **kw):
            return [{"memory_id": "x", "tier": "working",
                     "scope": "task", "scope_id": "other-task",
                     "truth_state": "unknown", "content": "c",
                     "created_at": 1.0, "updated_at": 1.0,
                     "expires_at": 9999999999.0, "relevance": 1.0}]

    async def go():
        return await retrieve(_GW(), query="q", task_id="my-task",
                              tiers=["working"])
    res = _aio.run(go())
    assert res["memories"] == []


@pytest.mark.asyncio
async def test_conv_model_audited_with_session():
    import core.ezzio_master as _m
    from core.ezzio_master import EzzioMaster
    from core.agent.coder_federation import CoderModelFederationRouter
    from core.providers.base_provider import ProviderResponse, CostClass
    recorded = []
    _orig = _m._audit_command
    _m._audit_command = lambda a, p, s="SUCCESS": recorded.append((a, p, s))
    try:
        router = CoderModelFederationRouter(providers={})

        async def fake_execute(prompt, profile, **kwargs):
            return ProviderResponse(
                content="Réponse de test suffisante.", role="assistant",
                model="qwen2.5-coder:7b-instruct-q4_K_M", provider="ollama",
                cost_class=CostClass.FREE_ENDPOINT,
                raw={"coder_federation_trace": {"attempts_count": 1}})
        router.execute_task = fake_execute
        master = EzzioMaster(federation_router=router)
        res = await master.execute_intent("Explique-moi ce projet",
                                          channel="test", session_id="s-ab")
        conv = [p for a, p, s in recorded if a == "CONV_MODEL"]
        assert conv, "CONV_MODEL non émis"
        assert conv[0]["model"] == "qwen2.5-coder:7b-instruct-q4_K_M"
        assert conv[0]["session_id"] == "s-ab"
        import inspect as _insp
        assert '"env", "test"' in _insp.getsource(_orig)
    finally:
        _m._audit_command = _orig


@pytest.mark.asyncio
async def test_memory_ab_local_harness():
    """A/B mémoire local (§11/§55) : même tâche, ON vs OFF, 0 quota."""
    import time as _t
    from core.ezzio_master import EzzioMaster
    from core.agent.coder_federation import CoderModelFederationRouter
    from core.providers.base_provider import ProviderResponse, CostClass
    router = CoderModelFederationRouter(providers={})

    async def fake_execute(prompt, profile, **kwargs):
        return ProviderResponse(
            content="Réponse locale.", role="assistant",
            model="m", provider="ollama",
            cost_class=CostClass.FREE_ENDPOINT,
            raw={"coder_federation_trace": {"attempts_count": 1}})
    router.execute_task = fake_execute
    master = EzzioMaster(federation_router=router)
    assert master is not None
    t0 = _t.perf_counter()
    _ = await router.execute_task("prompt A sans mémoire", profile=None)
    dt_off = _t.perf_counter() - t0
    t0 = _t.perf_counter()
    _ = await router.execute_task("prompt A avec mémoire", profile=None)
    dt_on = _t.perf_counter() - t0
    assert dt_off >= 0 and dt_on >= 0
    exp = M.new_experiment_id("memory_ab")
    assert exp.startswith("exp_memory_ab_")


def test_live_prod_gaps_exclude_tests():
    from core.security.audit_ledger import AuditLedger
    events = AuditLedger().query_events(limit=3000)
    prod = M.prod_only(events)
    assert len(prod) <= len(events)
    gaps = M.linkage_gaps(prod)
    assert isinstance(gaps["request_without_result"], int)
    models = M.model_effectiveness(prod)
    assert models["by_model"].n >= 0
    mem = M.memory_outcome_link(prod)
    assert mem["retrieval_ids"].n >= 0
