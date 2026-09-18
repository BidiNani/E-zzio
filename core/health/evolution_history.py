"""Historique longitudinal d'évolution — dérivé, borné, sans persistence propre.

Sources : AuditLedger existant (séries d'événements) + snapshots compacts que
l'appelant choisit d'y enregistrer (payloads ~200 o, cadence gouvernée).
Aucune table, aucun fichier, aucun état global : tout est pur et borné.
L'apprentissage porte sur données et décisions, jamais sur auto-mutation.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from enum import Enum
from typing import Any

MIN_SAMPLES_TREND = 5


class Trend(str, Enum):
    STABLE = "STABLE"
    IMPROVING = "IMPROVING"
    DEGRADING = "DEGRADING"
    OSCILLATING = "OSCILLATING"
    SPIKING = "SPIKING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    UNKNOWN = "UNKNOWN"


class Outcome(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    NO_GAIN = "NO_GAIN"
    REGRESSION = "REGRESSION"
    INCONCLUSIVE = "INCONCLUSIVE"
    ROLLED_BACK = "ROLLED_BACK"


@dataclass(frozen=True)
class SeriesStats:
    count: int
    first_seen: float
    last_seen: float
    minimum: float
    maximum: float
    mean: float
    median: float
    rate_per_day: float


def series_stats(values: list[tuple[float, float]]) -> SeriesStats | None:
    """(timestamp, valeur) → statistiques compactes. Vide = None, jamais zéro."""
    if not values:
        return None
    vs = sorted(values)
    vals = [v for _, v in vs]
    span_days = max((vs[-1][0] - vs[0][0]) / 86400.0, 1e-9)
    return SeriesStats(
        count=len(vs), first_seen=vs[0][0], last_seen=vs[-1][0],
        minimum=min(vals), maximum=max(vals),
        mean=round(statistics.fmean(vals), 4),
        median=round(statistics.median(vals), 4),
        rate_per_day=round(len(vs) / span_days, 4),
    )


def classify_trend(values: list[tuple[float, float]]) -> Trend:
    """Tendance déterministe sur valeurs ordonnées. n < 5 = INSUFFICIENT_DATA."""
    if len(values) < MIN_SAMPLES_TREND:
        return Trend.INSUFFICIENT_DATA
    vs = [v for _, v in sorted(values)]
    n = len(vs)
    half = n // 2
    early = statistics.fmean(vs[:half])
    late = statistics.fmean(vs[half:])
    span = max(vs) - min(vs)
    if span == 0:
        return Trend.STABLE
    rel = (late - early) / span
    last = vs[-1]
    # Pic récent isolé : discontinuité locale (dernier point très supérieur
    # à ses prédécesseurs immédiats). Une rampe régulière n'est pas un pic.
    # Les poussières sous le plancher de bruit sont filtrées en amont (moteur).
    prev = vs[-4:-1]
    med_prev = statistics.median(prev)
    if last > 3 * max(med_prev, span * 0.1) and last > med_prev:
        return Trend.SPIKING
    # Oscillation : signes alternés majoritaires entre segments consécutifs.
    diffs = [b - a for a, b in zip(vs, vs[1:])]
    signs = [1 if d > 0 else (-1 if d < 0 else 0) for d in diffs]
    flips = sum(1 for a, b in zip(signs, signs[1:]) if a * b < 0)
    if flips >= len(diffs) * 0.6 and span > 0:
        return Trend.OSCILLATING
    if rel >= 0.3:
        return Trend.DEGRADING  # valeurs croissantes = métrique qui se dégrade
    if rel <= -0.3:
        return Trend.IMPROVING
    return Trend.STABLE


def detect_recurrence(event_times: list[float], same_fingerprint: bool,
                      min_occurrences: int = 3) -> tuple[bool, float]:
    """Échec→réparation→échec répété = problème récurrent, pas incidents isolés."""
    if not same_fingerprint or len(event_times) < min_occurrences:
        return False, 0.0
    ts = sorted(event_times)
    gaps = [b - a for a, b in zip(ts, ts[1:])]
    mean_gap = statistics.fmean(gaps)
    # Confiance : occurrences nombreuses + intervalles du même ordre de grandeur.
    spread = (max(gaps) - min(gaps)) / max(mean_gap, 1e-9)
    conf = round(min(0.95, 0.5 + 0.1 * len(ts) - 0.1 * spread), 3)
    return True, max(conf, 0.0)


def detect_oscillation(recent_kinds: list[str]) -> bool:
    """A→B→A→B : gel d'évolution, retour à la cause racine."""
    seq = [k for k in recent_kinds if k]
    if len(seq) < 4:
        return False
    tail = seq[-4:]
    return tail[0] == tail[2] and tail[1] == tail[3] and tail[0] != tail[1]


def check_budget(window_changes: int, window_lines: int, window_risk: float,
                 max_changes: int = 3, max_lines: int = 300,
                 max_risk: float = 15.0) -> tuple[bool, str]:
    """Budget borné et gouverné : dépassé = STOP, même à signaux multiples."""
    if window_changes >= max_changes:
        return False, f"budget changements épuisé ({window_changes}/{max_changes})"
    if window_lines >= max_lines:
        return False, f"budget lignes épuisé ({window_lines}/{max_lines})"
    if window_risk >= max_risk:
        return False, f"budget risque épuisé ({window_risk}/{max_risk})"
    return True, "budget disponible"


def effectiveness(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    """Rapport implémentées/bénéfice démontré. Faible taux = attendre, pas forcer."""
    impl = [d for d in decisions if d.get("verdict") == "IMPLEMENT"]
    benefited = [d for d in impl if d.get("outcome") in ("SUCCESS", "PARTIAL")]
    return {
        "implemented": len(impl),
        "with_benefit": len(benefited),
        "ratio": round(len(benefited) / max(len(impl), 1), 3),
        "verdict": "INSUFFICIENT_DATA" if len(impl) < 3 else "MEASURED",
    }


def calibrate(predicted: list[float], actual_gain: list[bool]) -> dict[str, Any]:
    """Confiance prédite vs bénéfice réel. n<3 = non calibré, pas de conclusion."""
    pairs = [(p, a) for p, a in zip(predicted, actual_gain)]
    if len(pairs) < 3:
        return {"calibrated": False, "reason": "INSUFFICIENT_DATA"}
    high_conf = [a for p, a in pairs if p >= 0.8]
    hit = sum(1 for a in high_conf if a) / max(len(high_conf), 1)
    return {"calibrated": True,
            "high_confidence_hit_rate": round(hit, 3),
            "samples": len(pairs)}


def build_snapshot(signal_sizes: dict[str, float], health_system: str,
                   ledger_events: int) -> dict[str, Any]:
    """Snapshot compact (~200 o) destiné au ledger existant, pas à un store."""
    return {"kind": "HEALTH_SNAPSHOT", "system": health_system,
            "ledger_events": ledger_events,
            "signals": {k: v for k, v in signal_sizes.items()}}


def outcome_payload(proposal_id: str, expected: str, actual: str,
                    outcome: Outcome, rollback: str) -> dict[str, Any]:
    """Charge EVOLUTION_OUTCOME : attendu vs réel, vers le ledger existant."""
    return {"kind": "EVOLUTION_OUTCOME", "proposal_id": proposal_id,
            "expected": expected, "actual": actual,
            "outcome": outcome.value, "rollback": rollback}
