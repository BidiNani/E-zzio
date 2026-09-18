"""Sources de signaux d'évolution — collecte lecture seule, normalisation pure.

Séparation stricte : les fonctions collect_* effectuent l'I/O explicite
(fichiers/DB existants, jamais credentials ni réseau) ; normalize() est pure.
Un signal absent reste absent : jamais de zéro inventé (UNKNOWN explicite).
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

from core.health.evolution_decision import EvidenceClass


@dataclass(frozen=True)
class EvolutionSignal:
    signal_id: str  # ex: breaker:groq.tripped, ledger:TOOL_EXEC|PARTIAL.rate
    source: str  # composant émetteur (diagnostic, ledger, breaker, storage)
    timestamp: float
    value: float = 0.0
    baseline: float = 0.0
    unit: str = ""
    severity: str = "WATCH"  # WATCH | ANOMALY | REGRESSION | CRITICAL
    confidence: float = 0.0
    provenance: str = ""  # ex: change:<id> si auto-généré après modification
    evidence_class: EvidenceClass = EvidenceClass.MEASURED_NOW


def collect_diagnostic(now: float | None = None) -> list[dict[str, Any]]:
    """Signaux depuis l'observateur de santé existant (en mémoire)."""
    from core.health.diagnostic import full_diagnostic

    d = full_diagnostic()
    out = []
    for s in d.get("signals", []):
        if s.get("severity") in ("HEALTHY",):
            continue
        out.append({
            "signal_id": f"health:{s.get('signal_id', 'unknown')}",
            "source": "diagnostic",
            "timestamp": now or time.time(),
            "value": 1.0, "baseline": 0.0, "unit": "state",
            "severity": "ANOMALY" if s.get("severity") in ("SICK", "CRITICAL", "DEGRADED")
            else "WATCH",
            "confidence": 0.9,
            "provenance": "",
            "detail": str(s.get("detail", ""))[:200],
        })
    return out


def collect_breakers(state_path: str = "runtime/state/circuit_breakers.json",
                     now: float | None = None) -> list[dict[str, Any]]:
    """États disjoncteurs par provider. Fichier absent = aucun signal."""
    if not os.path.exists(state_path):
        return []
    try:
        data = json.load(open(state_path, encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for provider, st in (data.items() if isinstance(data, dict) else []):
        if not isinstance(st, dict):
            continue
        failures = float(st.get("failures", 0) or 0)
        if st.get("tripped"):
            out.append({
                "signal_id": f"breaker:{provider}.tripped",
                "source": "breaker", "timestamp": now or time.time(),
                "value": failures, "baseline": 0.0, "unit": "failures",
                "severity": "ANOMALY", "confidence": 0.95, "provenance": "",
            })
        elif failures > 0:
            out.append({
                "signal_id": f"breaker:{provider}.failures",
                "source": "breaker", "timestamp": now or time.time(),
                "value": failures, "baseline": 0.0, "unit": "failures",
                "severity": "WATCH", "confidence": 0.7, "provenance": "",
            })
    return out


def collect_ledger_rates(ledger=None, window_sec: float = 3600.0,
                         now: float | None = None) -> list[dict[str, Any]]:
    """Taux d'échec par action depuis le ledger (échecs/heure, observés)."""
    from core.security.audit_ledger import audit_ledger as default_ledger

    store = ledger or default_ledger
    ts = (now or time.time()) - window_sec
    try:
        hist = store.count_by_status_since(ts)
    except OSError:
        return []
    if not hist:
        return []
    totals: dict[str, float] = {}
    fails: dict[str, float] = {}
    for key, n in hist.items():
        action = key.split("|", 1)[0]
        totals[action] = totals.get(action, 0.0) + n
        if key.endswith("|PARTIAL") or key.endswith("|FAILED") or key.endswith("|ERROR"):
            fails[action] = fails.get(action, 0.0) + n
    out = []
    for action, bad in fails.items():
        rate = bad / max(totals.get(action, 1.0), 1.0)
        out.append({
            "signal_id": f"ledger:{action}.fail_rate",
            "source": "ledger", "timestamp": now or time.time(),
            "value": round(rate, 4), "baseline": 0.0, "unit": "ratio/h",
            "severity": "ANOMALY" if rate >= 0.5 else "WATCH",
            "confidence": 0.8, "provenance": "",
        })
    return out


# Fichiers observés pour la taille (constat seul : sans historique, pas de tendance).
STORAGE_WATCH = (
    "runtime/evidence/evidence.db",
    "runtime/evidence/audit_ledger.db",
    "ezzio.db",
    "state/cache/response_cache.db",
    "registry/cloud_cache",
)


def collect_storage(root: str = ".", now: float | None = None) -> list[dict[str, Any]]:
    """Tailles observées. evidence_class=NOT_MEASURED sur delta : aucune
    proposition de croissance ne peut naître d'une mesure unique."""
    out = []
    for rel in STORAGE_WATCH:
        p = os.path.join(root, rel)
        if os.path.isdir(p):
            size = 0
            for dp, _, fn in os.walk(p):
                for f in fn:
                    try:
                        size += os.path.getsize(os.path.join(dp, f))
                    except OSError:
                        pass
        elif os.path.exists(p):
            try:
                size = os.path.getsize(p)
            except OSError:
                continue
        else:
            continue
        out.append({
            "signal_id": f"storage:{rel}.bytes",
            "source": "storage", "timestamp": now or time.time(),
            "value": float(size), "baseline": 0.0, "unit": "bytes",
            "severity": "WATCH", "confidence": 0.5, "provenance": "",
            "trend": "UNKNOWN_SINGLE_SAMPLE",
        })
    return out


def normalize(raw: dict[str, Any]) -> EvolutionSignal:
    """Frontière unique : brut → signal typé. Pure, totale, sans I/O."""
    try:
        cls = EvidenceClass(raw.get("evidence_class", "MEASURED_NOW"))
    except ValueError:
        cls = EvidenceClass.UNVERIFIED
    return EvolutionSignal(
        signal_id=str(raw.get("signal_id", "unknown")),
        source=str(raw.get("source", "unknown")),
        timestamp=float(raw.get("timestamp", 0.0)),
        value=float(raw.get("value", 0.0)),
        baseline=float(raw.get("baseline", 0.0)),
        unit=str(raw.get("unit", "")),
        severity=str(raw.get("severity", "WATCH")),
        confidence=float(raw.get("confidence", 0.0)),
        provenance=str(raw.get("provenance", "")),
        evidence_class=cls,
    )
