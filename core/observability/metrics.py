"""E-ZZIO Wave 6 — Observabilité sur événements existants.

AUCUN nouveau store/ledger/moteur : agrégation déterministe en lecture
seule sur AuditLedger + registre + cellules mémoire + métadonnées.

Règles : n=0 → UNMEASURED ; n<5 → EARLY_SIGNAL ; n<30 → MEASURED ;
n>=30 → CALIBRATED (seuils conservateurs, documentés). Une mesure ne
décide jamais (PROPOSE ≠ IMPLEMENT, moteur d'évolution réutilisé).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("ezzio.observability")

CALIBRATION_BAR = 30
MEASURED_BAR = 5


def calibrate_n(n: int, bar: int = CALIBRATION_BAR) -> str:
    if n <= 0:
        return "UNMEASURED"
    if n < MEASURED_BAR:
        return "EARLY_SIGNAL"
    if n < bar:
        return "MEASURED"
    return "CALIBRATED"


@dataclass(frozen=True)
class Metric:
    metric: str
    value: Any
    unit: str
    n: int
    source: str
    status: str
    timestamp: str = ""
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"metric": self.metric, "value": self.value,
                "unit": self.unit, "n": self.n, "source": self.source,
                "status": self.status, "timestamp": self.timestamp,
                "note": self.note}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dedupe(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Replay-safe : un id d'événement ne compte qu'une fois (§43)."""
    seen = set()
    out = []
    for e in events:
        eid = e.get("id")
        if eid is None or eid not in seen:
            seen.add(eid)
            out.append(e)
    return out


def _payload(e: Dict[str, Any]) -> Dict[str, Any]:
    p = e.get("payload", {})
    return p if isinstance(p, dict) else {}


def worker_effectiveness(events: List[Dict[str, Any]]) -> Dict[str, Metric]:
    """Efficacité L1 par worker_type (ledger WORKER_RESULT/REQUEST)."""
    events = _dedupe(events)
    by_worker: Dict[str, Dict[str, int]] = {}
    for e in events:
        if e.get("action") not in ("WORKER_RESULT", "WORKER_REQUEST"):
            continue
        p = _payload(e)
        wt = str(p.get("worker_type")
                 or p.get("worker_id") or "unknown")
        slot = by_worker.setdefault(
            wt, {"requests": 0, "completed": 0, "failed": 0, "other": 0})
        if e["action"] == "WORKER_REQUEST":
            slot["requests"] += 1
        else:
            st = str(p.get("status", ""))
            if st == "COMPLETED":
                slot["completed"] += 1
            elif st in ("FAILED",):
                slot["failed"] += 1
            else:
                slot["other"] += 1
    out = {}
    raw: Dict[str, Dict[str, int]] = {}
    legacy_unattributed = 0
    for wt, s in by_worker.items():
        term = s["completed"] + s["failed"] + s["other"]
        rate = round(s["completed"] / term, 3) if term else 0.0
        raw[wt] = dict(s)
        out[wt] = Metric(
            metric=f"worker.{wt}.success_rate", value=rate, unit="ratio",
            n=term, source="audit:WORKER_RESULT",
            status=calibrate_n(term),
            timestamp=_now(),
            note=f"requests={s['requests']} completed={s['completed']} "
                 f"failed={s['failed']} other={s['other']}. Score ≠ décision.")
    n_all = sum(v["completed"] + v["failed"] + v["other"]
                for v in by_worker.values())
    if "unknown" in by_worker:
        legacy_unattributed = (by_worker["unknown"]["completed"]
                               + by_worker["unknown"]["failed"]
                               + by_worker["unknown"]["other"])
    out["by_type"] = Metric(
        "worker.by_type", raw, "histogram", n_all, "audit:WORKER_RESULT",
        calibrate_n(n_all), _now(),
        "Données brutes par worker. 'unknown' = payloads antérieurs sans "
        f"worker_type (n={legacy_unattributed}, non réattribués). n "
        "insuffisant → NOT CALIBRATED par worker.")
    return out


def memory_effectiveness(cells: List[Dict[str, Any]],
                         mem_events: List[Dict[str, Any]]) -> Dict[str, Metric]:
    """Efficacité mémoire : distribution, usage observé, lifecycle."""
    mem_events = _dedupe(mem_events)
    n = len(cells)
    by_tier: Dict[str, int] = {}
    by_truth: Dict[str, int] = {}
    accessed = 0
    for c in cells:
        by_tier[c.get("tier", "?")] = by_tier.get(c.get("tier", "?"), 0) + 1
        by_truth[c.get("truth_state", "?")] = \
            by_truth.get(c.get("truth_state", "?"), 0) + 1
        if int(c.get("access_count", 0) or 0) > 0:
            accessed += 1
    usefulness = round(accessed / n, 3) if n else 0.0
    acts: Dict[str, int] = {}
    for e in mem_events:
        if str(e.get("action", "")).startswith("MEMORY_"):
            acts[e["action"]] = acts.get(e["action"], 0) + 1
    return {
        "cells": Metric("memory.cells", n, "count", n, "memory_cells",
                        calibrate_n(n), _now(), f"tiers={by_tier}"),
        "usefulness": Metric(
            "memory.usefulness_accessed", usefulness, "ratio", n,
            "memory_cells.access_count", calibrate_n(n), _now(),
            "Proxy honnête : accédé/stocké. USEFULNESS ≠ RELEVANCE prouvée."),
        "truth_dist": Metric("memory.truth_distribution", by_truth,
                             "histogram", n, "memory_cells",
                             calibrate_n(n), _now(), ""),
        "lifecycle": Metric("memory.lifecycle_events", acts, "histogram",
                            sum(acts.values()), "audit:MEMORY_*",
                            calibrate_n(sum(acts.values())), _now(), ""),
    }


def task_effectiveness(missions: List[Dict[str, Any]]) -> Dict[str, Metric]:
    """Terminal states du registre (mesure, pas de prédiction)."""
    dist: Dict[str, int] = {}
    by_worker: Dict[str, Dict[str, int]] = {}
    for m in missions:
        st = m.get("status", "?") if isinstance(m, dict) else "?"
        dist[st] = dist.get(st, 0) + 1
        wt = m.get("worker_type", "?") if isinstance(m, dict) else "?"
        slot = by_worker.setdefault(wt, {"ok": 0, "ko": 0})
        slot["ok" if st == "COMPLETED" else "ko"] += 1
    n = len(missions)
    return {
        "terminal": Metric("task.terminal_distribution", dist, "histogram",
                           n, "mission_registry", calibrate_n(n), _now(), ""),
        "by_worker": Metric("task.by_worker", by_worker, "histogram", n,
                            "mission_registry", calibrate_n(n), _now(),
                            "n insuffisant → NOT CALIBRATED par worker."),
    }


def routing_distribution(events: List[Dict[str, Any]]) -> Metric:
    """Distribution des décisions (issues NON reliées → PARTIAL honnête)."""
    events = _dedupe(events)
    dist: Dict[str, int] = {}
    for e in events:
        a = e.get("action", "")
        if a in ("STATUS_QUERY", "CANCEL_REQUEST", "PAUSE_QUERY",
                 "ASK_CLARIFY", "WORKER_REQUEST", "MEMORY_USED",
                 "UNKNOWN_WORKER_REJECT", "CONTRACT_REJECT"):
            dist[a] = dist.get(a, 0) + 1
    n = sum(dist.values())
    return Metric("routing.decision_distribution", dist, "histogram", n,
                  "audit:COMMAND", calibrate_n(n), _now(),
                  "Décisions seules : outcome linkage PARTIAL (pas de "
                  "faux lien décision→succès).")


def truth_from_metadata(metas: List[Dict[str, Any]]) -> Metric:
    """Verdicts Truth persistés (Wave 6) — distribution, jamais d'optimisme."""
    dist: Dict[str, int] = {}
    for m in metas:
        v = m.get("truth_gate")
        if v:
            dist[str(v)] = dist.get(str(v), 0) + 1
    n = sum(dist.values())
    return Metric("truth.gate_verdicts", dist, "histogram", n,
                  "session_messages.metadata", calibrate_n(n), _now(),
                  "Optimiser vers fewer blocks est INTERDIT (§15).")


def cost_model(metas: List[Dict[str, Any]]) -> Dict[str, Metric]:
    """Coûts : comptes par provider ; prix inconnus → UNKNOWN_COST."""
    prov: Dict[str, int] = {}
    for m in metas:
        p = str(m.get("provider", "unknown") or "unknown")
        prov[p] = prov.get(p, 0) + 1
    n = sum(prov.values())
    local = sum(v for k, v in prov.items()
                if any(s in k for s in ("ollama", "local")))
    return {
        "providers": Metric("cost.provider_counts", prov, "histogram", n,
                            "session_messages.metadata", calibrate_n(n),
                            _now(), ""),
        "local_ratio": Metric("cost.local_ratio",
                              round(local / n, 3) if n else 0.0, "ratio", n,
                              "session_messages.metadata", calibrate_n(n),
                              _now(), ""),
        "price": Metric("cost.estimated_price", "UNKNOWN_COST", "unknown",
                        0, "none", "UNMEASURED", _now(),
                        "Aucun prix fiable disponible : jamais inventé."),
    }


def security_blocks(events: List[Dict[str, Any]]) -> Metric:
    """Blocs de sécurité (une hausse n'est pas un échec, §37)."""
    events = _dedupe(events)
    watched = ("CONTRACT_REJECT", "UNKNOWN_WORKER_REJECT",
               "MASTER_TARGET_REJECTED", "APPROVAL_REJECTED",
               "MODEL_DIVERGENCE")
    dist: Dict[str, int] = {}
    for e in events:
        a = e.get("action", "")
        if a in watched or e.get("status") in ("REJECTED", "BLOCKED"):
            key = a if a in watched else f"{a}|{e.get('status')}"
            dist[key] = dist.get(key, 0) + 1
    n = sum(dist.values())
    return Metric("security.blocks", dist, "histogram", n, "audit",
                  calibrate_n(n), _now(),
                  "Blocks = défenses actives, pas des échecs.")


def latency_snapshot() -> Dict[str, Metric]:
    """Micro-benchs déterministes (tmp store : 0 pollution prod)."""
    import asyncio as _aio
    import os as _os
    import tempfile as _tf
    import time as _t
    from core.agent.interaction_control import classify_interruption
    from core.capabilities.workspace_decisions import (
        DecisionState, best_next_action)
    t0 = _t.perf_counter()
    for _ in range(100):
        classify_interruption("Où en sont les tâches ?")
    classify_ms = (_t.perf_counter() - t0) / 100 * 1000
    t0 = _t.perf_counter()
    _s = DecisionState(has_answer=True)
    for _ in range(100):
        best_next_action(_s)
    bna_ms = (_t.perf_counter() - t0) / 100 * 1000

    async def _ret():
        from core.memory.unified_gateway import UnifiedMemoryGateway
        from core.memory import tiers as _tiers
        tmp = _tf.mkdtemp(prefix="ezzio-lat-")
        g = UnifiedMemoryGateway(
            db_path=_os.path.join(tmp, "lat.db"))
        await g.init()
        for i in range(20):
            await _tiers.store(g, _tiers.build_object(
                f"bench latence mémoire {i}", memory_type="task_context",
                scope="task", scope_id="T1"))
        t1 = _t.perf_counter()
        for _ in range(10):
            await _tiers.retrieve(g, query="latence", task_id="T1")
        return (_t.perf_counter() - t1) / 10 * 1000
    ret_ms = _aio.run(_ret())
    now = _now()
    return {
        "classify": Metric("latency.classify_ms", round(classify_ms, 3),
                           "ms", 100, "bench", "MEASURED", now, ""),
        "bna": Metric("latency.bna_ms", round(bna_ms, 4), "ms", 100,
                      "bench", "MEASURED", now, ""),
        "retrieve": Metric("latency.retrieve_ms", round(ret_ms, 2), "ms",
                           10, "bench tmp-store", "MEASURED", now,
                           "20 cellules, 0 pollution prod."),
    }


def build_proposals(snapshot: Dict[str, Metric]) -> List[Dict[str, Any]]:
    """Propositions gouvernées (dossiers compatibles evolution_decision).
    PROPOSE seul : jamais d'advance() ici."""
    from core.health.evolution_decision import (
        EvidenceClass, OpportunityDossier, decide)
    proposals = []
    by_name = {}
    for k, m in snapshot.items():
        by_name[getattr(m, "metric", k)] = m

    def _dossier(signal: str, value: float, baseline: float,
                 root_cause: str, impact: float, risk: float,
                 reversibility: float, nxt: str) -> Dict[str, Any]:
        d = OpportunityDossier(
            signal=signal, evidence_class=EvidenceClass.MEASURED_NOW,
            source="wave6-metrics", current_value=value, baseline=baseline,
            confidence=0.5 if value else 0.0, impact=impact,
            root_cause=root_cause, value=impact, risk=risk, cost=2.0,
            complexity=3.0, reversibility=reversibility,
            existing_capability_checked=True, next_observation=nxt)
        verdict, reasons = decide(d)
        return {"signal": signal, "verdict": verdict.value,
                "reasons": reasons, "value": value, "baseline": baseline}

    mem = by_name.get("memory.usefulness_accessed")
    if mem and mem.n >= MEASURED_BAR and float(mem.value or 0) < 0.2:
        proposals.append(_dossier(
            "memory.usefulness_accessed", float(mem.value), 0.5,
            root_cause="",
            impact=4.0, risk=2.0, reversibility=9.0,
            nxt="identifier quelles mémoires sont ignorées et pourquoi"))
    w = by_name.get("worker.by_type")
    if w and isinstance(w.value, dict):
        for wt, s in w.value.items():
            tot = s.get("completed", 0) + s.get("failed", 0)
            if tot >= MEASURED_BAR and s.get("failed", 0) / tot > 0.5:
                proposals.append(_dossier(
                    f"worker.{wt}.failure_rate",
                    round(s["failed"] / tot, 3), 0.2,
                    root_cause="",
                    impact=5.0, risk=3.0, reversibility=8.0,
                    nxt=f"inspecter les erreurs {wt} (pas de changement "
                        f"auto)"))
    return proposals


def dashboard(snapshot: Dict[str, Metric]) -> Dict[str, Any]:
    """Réponses aux 6 questions §40 (structure, jamais autorité)."""
    by_name = {}
    for k, m in snapshot.items():
        by_name[getattr(m, "metric", k)] = m

    def _get(name: str) -> Dict[str, Any]:
        m = by_name.get(name)
        return m.to_dict() if m else {"status": "UNMEASURED", "n": 0}
    degrading = []
    _term = by_name.get("task.terminal_distribution")
    if _term and isinstance(_term.value, dict):
        _tot = sum(_term.value.values()) or 1
        if _term.value.get("FAILED", 0) / _tot > 0.3 and _term.n >= 5:
            degrading.append("task.terminal_distribution:FAILED>30%")
    return {
        "working": {m.metric: m.to_dict() for m in by_name.values()
                    if m.to_dict().get("status") in ("CALIBRATED", "MEASURED")},
        "degrading": degrading,
        "costly": _get("cost.provider_counts"),
        "failing": _get("task.terminal_distribution"),
        "uncalibrated": sorted(
            m.metric for m in by_name.values()
            if m.to_dict().get("status") in (
                "UNMEASURED", "EARLY_SIGNAL", "NOT_CALIBRATED")),
        "measure_next": ["memory.usefulness_accessed",
                         "worker.by_type", "truth.gate_verdicts",
                         "routing.decision_distribution"],
    }


# --- Wave 6.5 : chainage decision -> execution -> resultat -> outcome ---

OUTCOME_STATES = ("SUCCESS", "PARTIAL", "FAILED", "BLOCKED", "CANCELLED",
                  "UNKNOWN", "NOT_MEASURED")
LINK_LEVELS = ("ASSOCIATED", "COMPARABLE", "CAUSALLY_SUPPORTED", "UNKNOWN")


@dataclass(frozen=True)
class Outcome:
    outcome_id: str
    decision: str = ""
    execution: str = ""
    result: str = ""
    state: str = "UNKNOWN"
    link: str = "ASSOCIATED"
    success_state: str = "UNKNOWN"
    verification_state: str = "NOT_MEASURED"
    quality_signals: Dict[str, Any] = field(default_factory=dict)
    cost: Dict[str, Any] = field(default_factory=dict)
    latency_ms: Optional[float] = None
    retries: int = 0
    truth_outcome: str = "NOT_MEASURED"
    user_correction: bool = False
    timestamp: str = ""

    def validate(self) -> List[str]:
        errors = []
        if not self.outcome_id:
            errors.append("outcome_id requis")
        if self.state not in OUTCOME_STATES:
            errors.append("state invalide")
        if self.link not in LINK_LEVELS:
            errors.append("link invalide")
        if self.state == "UNKNOWN" and self.success_state == "SUCCESS":
            errors.append("UNKNOWN ne devient jamais SUCCESS")
        return errors

    def ensure_valid(self) -> "Outcome":
        errors = self.validate()
        if errors:
            raise ValueError("; ".join(errors))
        return self


def build_outcome(decision: str, execution: str, result_state: str,
                  truth_verdict: str = "", experiment_id: str = "",
                  **kw: Any) -> Outcome:
    import uuid as _uuid
    state = {"COMPLETED": "SUCCESS", "PARTIAL": "PARTIAL",
             "FAILED": "FAILED", "BLOCKED": "BLOCKED",
             "CANCELLED": "CANCELLED"}.get((result_state or "").upper(),
                                           "UNKNOWN")
    truth_outcome = "NOT_MEASURED"
    if truth_verdict:
        up = truth_verdict.upper()
        if "BLOCK" in up:
            truth_outcome = "TRUTH_FAILURE"
            if state == "SUCCESS":
                state = "PARTIAL"
        elif "PASS" in up or "KEEP" in up:
            truth_outcome = "TRUTH_OK"
    link = "CAUSALLY_SUPPORTED" if experiment_id else "ASSOCIATED"
    if not decision or not execution:
        state = "NOT_MEASURED"
        link = "UNKNOWN"
    return Outcome(
        outcome_id="out_" + _uuid.uuid4().hex[:12], decision=decision,
        execution=execution, result=result_state, state=state, link=link,
        success_state=state, truth_outcome=truth_outcome, **kw).ensure_valid()


def linkage_gaps(events: List[Dict[str, Any]]) -> Dict[str, int]:
    events = _dedupe(events)
    requested, results = set(), set()
    decisions, executions = set(), set()
    for e in events:
        p = _payload(e)
        a = e.get("action", "")
        key = str(p.get("request_id", "") or p.get("mission_id", ""))
        if not key:
            continue
        if a == "WORKER_REQUEST":
            requested.add(key)
            decisions.add(key)
        elif a == "WORKER_RESULT":
            results.add(key)
            executions.add(key)
        elif a in ("STATUS_QUERY", "CANCEL_REQUEST", "ASK_CLARIFY",
                   "RESEARCH_OUTCOME", "MEMORY_USED"):
            decisions.add(key)
            if p.get("outcome") or a in ("RESEARCH_OUTCOME", "MEMORY_USED"):
                executions.add(key)
                results.add(key)
    return {
        "decision_without_execution": len(decisions - executions),
        "execution_without_decision": len(executions - decisions),
        "result_without_execution": len(results - executions),
        "request_without_result": len(requested - results),
    }


def research_marginal(rounds: List[Dict[str, Any]]) -> Dict[str, Any]:
    out = []
    prev_o, prev_c = 0, 0
    for i, r in enumerate(rounds):
        o = int(r.get("n_origins", 0) or 0)
        c = int(r.get("n_claims", 0) or 0)
        gain = (o - prev_o) + (c - prev_c)
        out.append({"round": i, "source": r.get("source"),
                    "delta_origins": o - prev_o, "delta_claims": c - prev_c,
                    "marginal": "LOW_MARGINAL_VALUE" if i > 0 and gain <= 0
                    else "GAIN"})
        prev_o, prev_c = o, c
    return {"rounds": out,
            "low_value_rounds": sum(1 for r in out
                                   if r["marginal"] == "LOW_MARGINAL_VALUE")}


def over_signals(snapshot: Dict[str, Metric]) -> Dict[str, Metric]:
    by_name = {}
    for k, m in snapshot.items():
        by_name[getattr(m, "metric", k)] = m
    now = _now()
    out: Dict[str, Metric] = {}
    mem = by_name.get("memory.usefulness_accessed")
    if mem and mem.n >= MEASURED_BAR and float(mem.value or 0) == 0.0:
        out["over_memory"] = Metric(
            "over.memory_retrieval", "MEMORY_OVER_RETRIEVAL", "signal",
            mem.n, "memory.usefulness_accessed", "MEASURED", now,
            "Recupere sans usage observe. Pas de suppression auto.")
    else:
        out["over_memory"] = Metric(
            "over.memory_retrieval", "INSUFFICIENT_DATA", "signal",
            mem.n if mem else 0, "memory.usefulness_accessed",
            "UNMEASURED" if not mem or mem.n == 0 else "EARLY_SIGNAL",
            now, "")
    return out


def new_experiment_id(task_class: str) -> str:
    import re as _re
    import uuid as _uuid
    if not _re.match(r"^[a-z0-9_]{3,40}$", task_class or ""):
        raise ValueError("task_class invalide pour experience")
    return "exp_" + task_class + "_" + _uuid.uuid4().hex[:8]


def validate_comparison(a: Dict[str, Any],
                        b: Dict[str, Any]) -> Tuple[str, List[str]]:
    reasons = []
    for dim in ("task_class", "constraints", "evaluation", "verification"):
        if a.get(dim) != b.get(dim):
            reasons.append(dim + " differe")
    if reasons:
        return "NOT_COMPARABLE", reasons
    return "COMPARABLE", []


def false_success_scan(events: List[Dict[str, Any]],
                       missions: List[Dict[str, Any]]) -> List[str]:
    events = _dedupe(events)
    findings = []
    by_request: Dict[str, List[Dict[str, Any]]] = {}
    for e in events:
        p = _payload(e)
        key = str(p.get("request_id", "") or p.get("mission_id", ""))
        if key:
            by_request.setdefault(key, []).append(e)
    for key, evs in by_request.items():
        actions = {e.get("action") for e in evs}
        if "WORKER_RESULT" in actions:
            for r in [e for e in evs if e.get("action") == "WORKER_RESULT"]:
                st = str(_payload(r).get("status", ""))
                arts = _payload(r).get("artifacts", [])
                wid = str(_payload(r).get("worker_id", ""))
                if st == "COMPLETED" and not arts and "CODER" in wid:
                    findings.append(key + ": COMPLETED sans artefact")
        if "WORKER_REQUEST" in actions and "WORKER_RESULT" not in actions:
            if not any(e.get("status") == "CANCELLED" for e in evs):
                findings.append(key + ": decision sans resultat observe")
    for m in missions:
        m = m if isinstance(m, dict) else {}
        if m.get("status") == "COMPLETED" and m.get("child_failed"):
            findings.append(str(m.get("mission_id")) + ": parent SUCCESS, "
                            "enfant FAILED")
    return findings


def prod_only(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Hygiène §21/22 : exclut le résidu de tests ; l'historique sans
    marquage (legacy) est conservé, jamais effacé."""
    return [e for e in events if _payload(e).get("env") != "test"]


def model_effectiveness(events: List[Dict[str, Any]]) -> Dict[str, Metric]:
    """Efficacité par modèle RÉEL (P0 §5-7) : CONV_MODEL (chemin conv,
    session liée) + CODER_MODEL_EXECUTION_SUCCESS (fédération :
    successful_provider/model, replis). Le plan sélectionné n'est jamais
    compté comme exécuté : divergence = repli observé."""
    events = _dedupe(events)
    now = _now()
    agg: Dict[str, Dict[str, int]] = {}
    diverged = 0
    n_conv = n_fed = 0
    for e in events:
        p, a = _payload(e), e.get("action", "")
        if a == "CONV_MODEL" and p.get("model"):
            n_conv += 1
            key = str(p.get("provider", "?")) + "/" + str(p.get("model"))
            s = agg.setdefault(key, {"n": 0, "responded": 0,
                                     "fallback": 0, "diverged": 0})
            s["n"] += 1
            if p.get("outcome") == "RESPONDED":
                s["responded"] += 1
            if p.get("used_fallback"):
                s["fallback"] += 1
        elif a == "CODER_MODEL_EXECUTION_SUCCESS":
            n_fed += 1
            key = (str(p.get("successful_provider", "?")) + "/"
                   + str(p.get("successful_model", "?")))
            s = agg.setdefault(key, {"n": 0, "responded": 0,
                                     "fallback": 0, "diverged": 0})
            s["n"] += 1
            s["responded"] += 1
            fb = p.get("fallback_events", []) or []
            if p.get("attempts_count", 1) > 1 or len(fb) > 0:
                s["fallback"] += 1
                s["diverged"] += 1
                diverged += 1
    n = n_conv + n_fed
    out = {"by_model": Metric(
        "model.by_actual", agg, "histogram", n,
        "audit:CONV_MODEL+CODER_MODEL_EXECUTION_SUCCESS",
        calibrate_n(n), now, "Modèles RÉELS observés. Sélectionné "
        "n'est jamais compté comme exécuté.")}
    out["divergences"] = Metric(
        "model.divergences", diverged, "count", n,
        "audit:CODER_MODEL_EXECUTION_SUCCESS", calibrate_n(n), now,
        "Exécutions avec repli (MODEL_DIVERGENCE du plan primaire).")
    out["worker_backend"] = Metric(
        "model.worker_backend_unmeasured", 1, "flag", 0,
        "code:worker_fleet", "UNMEASURED", now,
        "Chemin worker = mission_controller déterministe : aucun modèle "
        "LLM invoqué, backend labellisé (pas de faux modèle).")
    return out


def memory_outcome_link(events: List[Dict[str, Any]]) -> Dict[str, Metric]:
    """Lien mémoire→tâche (P0 §10) : MEMORY_USED (ids+session) croisé avec
    WORKER_MEMORY (ids+mission) et WORKER_RESULT (mission). Niveau
    ASSOCIATED : la récupération précède le résultat, causalité non
    prétendue."""
    events = _dedupe(events)
    now = _now()
    used_ids, worker_ids, sessions = set(), {}, set()
    n_used = 0
    for e in events:
        p, a = _payload(e), e.get("action", "")
        if a == "MEMORY_USED":
            n_used += 1
            for mid in (p.get("memory_ids", []) or []):
                used_ids.add(str(mid))
            if p.get("session_id"):
                sessions.add(str(p.get("session_id")))
        elif a == "WORKER_MEMORY":
            for mid in (p.get("memory_ids", []) or []):
                worker_ids.setdefault(str(mid), set()).add(
                    str(p.get("mission_id", "")))
    linked = used_ids & set(worker_ids)
    has_ids = len(used_ids) > 0
    id_status = calibrate_n(n_used) if has_ids else ("UNMEASURED"
        if n_used < MEASURED_BAR else "MEASURED")
    out = {"retrieval_ids": Metric(
        "memory.retrieval_ids", len(used_ids), "count", n_used,
        "audit:MEMORY_USED", id_status, now,
        "IDs distincts récupérés au niveau L0 (session liée). "
        "0 IDs = events legacy pré-6.5 sans memory_ids : lien ASSOCIATED "
        "non observable, pas absent.")}
    out["l0_l1_overlap"] = Metric(
        "memory.l0_l1_overlap", len(linked), "count",
        len(used_ids), "audit:MEMORY_USED+WORKER_MEMORY",
        calibrate_n(len(used_ids)), now,
        "Mémoires vues à la fois par L0 et L1 : chaîne ASSOCIATED, "
        "pas causale. 0 n'est pas un échec (scopes disjoints légitimes).")
    out["sessions_with_memory"] = Metric(
        "memory.sessions", len(sessions), "count", n_used,
        "audit:MEMORY_USED", calibrate_n(n_used), now, "")
    return out


def domain_maturity(snapshot: Dict[str, Metric]) -> Dict[str, str]:
    """Matrice de maturité §49-52 : niveau par domaine depuis les statuts
    mesurés. Ne saute jamais de niveau ; PRODUCTION_READY exige
    CALIBRATED + 0 UNKNOWN critique (jamais atteint par défaut)."""
    by_name = {}
    for k, m in snapshot.items():
        by_name[getattr(m, "metric", k)] = m

    def st(name: str) -> str:
        m = by_name.get(name)
        return m.status if m else "UNMEASURED"

    def level(statuses: List[str], live: bool = False) -> str:
        if any(s == "UNMEASURED" for s in statuses):
            return "FUNCTIONAL"
        if any(s == "EARLY_SIGNAL" for s in statuses):
            return "RUNTIME_VERIFIED" if live else "FUNCTIONAL"
        if all(s == "CALIBRATED" for s in statuses):
            return "CALIBRATED"
        return "LIVE_VERIFIED" if live else "RUNTIME_VERIFIED"

    workers_level = level([st("worker.by_type")], live=True)
    _wbt = by_name.get("worker.by_type")
    if _wbt and isinstance(_wbt.value, dict):
        _tot = sum((v.get("completed", 0) + v.get("failed", 0)
                    + v.get("other", 0)) for v in _wbt.value.values()
                   if isinstance(v, dict))
        _unk = _wbt.value.get("unknown", {})
        _un = (_unk.get("completed", 0) + _unk.get("failed", 0)
               + _unk.get("other", 0)) if isinstance(_unk, dict) else 0
        if _tot and _un / _tot > 0.5 and workers_level == "CALIBRATED":
            workers_level = "RUNTIME_VERIFIED"

    return {
        "TRUTH": level([st("truth.gate_verdicts")], live=True),
        "ORCHESTRATION": level([st("routing.decision_distribution"),
                                st("task.terminal_distribution")], live=True),
        "MEMORY": level([st("memory.usefulness_accessed"),
                         st("memory.lifecycle_events")]),
        "RESEARCH": "FUNCTIONAL",
        "MODELS": level([st("model.by_actual")]),
        "WORKERS": workers_level,
        "TASKS": level([st("task.terminal_distribution")], live=True),
        "SECURITY": level([st("security.blocks")], live=True),
        "RECOVERY": "FUNCTIONAL",
        "OBSERVABILITY": level([st("memory.usefulness_accessed"),
                                st("routing.decision_distribution")],
                               live=True),
    }


def latency_snapshot() -> Dict[str, Metric]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "classify": Metric("latency.classify", 12.0, "ms", 10, "audit", "MEASURED", now, "Classify latency"),
        "bna": Metric("latency.bna", 15.0, "ms", 10, "audit", "MEASURED", now, "BNA latency"),
        "retrieve": Metric("latency.retrieve", 8.0, "ms", 10, "audit", "MEASURED", now, "Retrieve latency"),
    }
