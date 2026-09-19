"""Moteur de décision d'évolution — borné, pur, sans autorité.

Responsabilité unique : observer → interpréter → qualifier → prioriser → proposer.
NE décide jamais : authorize / implement / execute / audit / rollback.
Ces pouvoirs restent aux autorités existantes (policy, registry, tests, ledger).

Toutes les fonctions sont pures (aucune I/O, aucun état global) : le score est
reproductible et le verdict est explicable (liste de raisons jointe).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class EvidenceClass(StrEnum):
    PROVEN = "PROVEN"
    MEASURED_NOW = "MEASURED_NOW"
    REUSED_BASELINE = "REUSED_BASELINE"
    NOT_MEASURED = "NOT_MEASURED"
    UNKNOWN = "UNKNOWN"
    UNVERIFIED = "UNVERIFIED"


class OpportunityState(StrEnum):
    OBSERVED = "OBSERVED"
    CONFIRMED = "CONFIRMED"
    ROOT_CAUSED = "ROOT_CAUSED"
    QUALIFIED = "QUALIFIED"
    PROPOSED = "PROPOSED"
    IMPLEMENTED = "IMPLEMENTED"
    TESTED = "TESTED"
    BENCHMARKED = "BENCHMARKED"
    CERTIFIED = "CERTIFIED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"
    ROLLED_BACK = "ROLLED_BACK"
    QUARANTINED = "QUARANTINED"


# Transitions autorisées ; le moteur n'avance jamais au-delà de PROPOSED
# (l'approbation externe appartient à la gouvernance existante).
ALLOWED_TRANSITIONS: dict[OpportunityState, tuple[OpportunityState, ...]] = {
    OpportunityState.OBSERVED: (OpportunityState.CONFIRMED, OpportunityState.REJECTED),
    OpportunityState.CONFIRMED: (OpportunityState.ROOT_CAUSED, OpportunityState.REJECTED),
    OpportunityState.ROOT_CAUSED: (OpportunityState.QUALIFIED, OpportunityState.DEFERRED,
                                   OpportunityState.REJECTED),
    OpportunityState.QUALIFIED: (OpportunityState.PROPOSED, OpportunityState.DEFERRED,
                                 OpportunityState.REJECTED, OpportunityState.QUARANTINED),
    OpportunityState.PROPOSED: (OpportunityState.REJECTED, OpportunityState.DEFERRED),
}


class Verdict(StrEnum):
    IMPLEMENT = "IMPLEMENT"  # proposition vers la gouvernance (pas une autorisation)
    DEFER = "DEFER"
    REJECT = "REJECT"
    KEEP = "KEEP"  # abstention explicite : système sain, aucun gain
    MEASURE = "MEASURE"  # incertitude levable par une observation peu coûteuse


@dataclass(frozen=True)
class OpportunityDossier:
    signal: str
    evidence_class: EvidenceClass
    observation_time: str = ""
    source: str = ""
    current_value: float = 0.0
    baseline: float = 0.0
    noise_floor: float = 0.0  # sous ce delta : théâtre, pas d'évolution
    confidence: float = 0.0  # 0..1
    impact: float = 0.0  # 0..10
    root_cause: str = ""  # vide = symptôme seul → non qualifiable
    value: float = 0.0  # 0..10
    risk: float = 0.0  # 0..10
    cost: float = 0.0  # 0..10
    complexity: float = 0.0  # 0..10
    reversibility: float = 0.0  # 0..10 (10 = rollback trivial)
    creates_authority: bool = False
    touches_rejected_model: bool = False
    self_modifies_governance: bool = False
    existing_capability_checked: bool = False
    frequency: float = 0.0  # occurrences / jour, 0 = ponctuel
    next_observation: str = ""  # observation peu coûteuse levant l'incertitude (§14)


def score_opportunity(d: OpportunityDossier) -> tuple[float, list[str]]:
    """Score déterministe et explicable. Ne décide jamais seul (cf. decide)."""
    reasons = [
        f"value={d.value}",
        f"evidence={d.evidence_class.value}",
        f"impact={d.impact}",
        f"confidence={d.confidence}",
        f"frequency={d.frequency}/j",
        f"risk={d.risk}",
        f"cost={d.cost}",
        f"complexity={d.complexity}",
    ]
    score = (d.value + d.impact + d.confidence * 10.0 + min(d.frequency, 10.0)
             - d.risk - d.cost - d.complexity)
    return round(score, 3), reasons


def decide(d: OpportunityDossier) -> tuple[Verdict, list[str]]:
    """Fail-closed : tout doute → DEFER ; toute violation → REJECT."""
    # Hard gates d'abord (aucun score ne les rachète).
    if d.creates_authority:
        return Verdict.REJECT, ["creates_authority: seconde autorité interdite"]
    if d.touches_rejected_model:
        return Verdict.REJECT, ["touches_rejected_model: REJECTED = NEVER ROUTED"]
    if d.self_modifies_governance:
        return Verdict.REJECT, ["self_modifies_governance: la gouvernance est au-dessus"]
    if d.evidence_class in (EvidenceClass.UNKNOWN, EvidenceClass.NOT_MEASURED,
                            EvidenceClass.UNVERIFIED):
        return Verdict.DEFER, [f"evidence={d.evidence_class.value}: preuve insuffisante"]
    if not d.root_cause:
        if d.next_observation and d.risk <= 3.0:
            return Verdict.MEASURE, [f"mesurer d'abord : {d.next_observation}"]
        return Verdict.DEFER, ["root_cause vide: symptôme seul, pas d'opportunité"]
    if not d.existing_capability_checked:
        return Verdict.DEFER, ["existing-first non vérifié"]
    delta = abs(d.current_value - d.baseline)
    if d.noise_floor > 0 and delta <= d.noise_floor:
        return Verdict.DEFER, [f"delta={delta} <= noise={d.noise_floor}: théâtre, NO CHANGE"]
    if d.value <= 0:
        return Verdict.KEEP, ["value nulle: abstention, système inchangé"]
    score, reasons = score_opportunity(d)
    if score < 0:
        return Verdict.DEFER, [f"score={score} < 0: risque/coût > valeur"] + reasons
    return Verdict.IMPLEMENT, [f"score={score}: proposition vers gouvernance"] + reasons


def advance(state: OpportunityState, target: OpportunityState) -> OpportunityState:
    """Transition fermée ; lève ValueError sur saut silencieux ou auto-approbation."""
    allowed = ALLOWED_TRANSITIONS.get(state, ())
    if target not in allowed:
        raise ValueError(f"transition interdite: {state.value} → {target.value}")
    return target


def to_ledger_payload(d: OpportunityDossier, verdict: Verdict,
                      reasons: list[str]) -> dict[str, Any]:
    """Charge minimale pour l'AuditLedger existant (aucune écriture ici)."""
    return {
        "signal": d.signal,
        "evidence_class": d.evidence_class.value,
        "source": d.source,
        "baseline": d.baseline,
        "current_value": d.current_value,
        "root_cause": d.root_cause or "UNKNOWN",
        "verdict": verdict.value,
        "reasons": reasons,
    }


class BenchmarkOutcome(StrEnum):
    MEASURABLE_GAIN = "MEASURABLE_GAIN"
    NO_MEASURABLE_GAIN = "NO_MEASURABLE_GAIN"
    REGRESSION = "REGRESSION"
    INCONCLUSIVE = "INCONCLUSIVE"


def classify_benchmark(before: float, after: float, noise: float,
                       samples: int, lower_is_better: bool = True) -> BenchmarkOutcome:
    """Avant/après déterministe. Échantillons insuffisants = INCONCLUSIVE."""
    if samples < 3 or noise <= 0:
        return BenchmarkOutcome.INCONCLUSIVE
    delta = (before - after) if lower_is_better else (after - before)
    if abs(delta) <= noise:
        return BenchmarkOutcome.NO_MEASURABLE_GAIN
    return (BenchmarkOutcome.MEASURABLE_GAIN if delta > 0
            else BenchmarkOutcome.REGRESSION)
