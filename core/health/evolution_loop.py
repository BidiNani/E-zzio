"""Boucle d'évolution live — pure, bornée, sans autorité.

Chaîne : signaux normalisés → faisceau corrélé → cause → existing-first →
dossier → decide() → proposition PROPOSED → gouvernance externe.
Anti-tempête (empreinte + ensemble actif fournis par l'appelant, aucun état
global) et anti-boucle (signaux auto-générés marqués, verdict DEFER sauf
CRITICAL). N'écrit rien, n'exécute rien, n'approuve rien.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Collection, Dict, List, Optional, Tuple

from core.health.evolution_decision import (
    EvidenceClass, OpportunityDossier, OpportunityState, Verdict, advance, decide,
)
from core.health.evolution_signals import EvolutionSignal


# Table déterministe signal → (catégorie cause, confiance). Défaut = UNKNOWN.
ROOT_CAUSE_MAP: Tuple[Tuple[str, str, float], ...] = (
    ("breaker:", "PROVIDER", 0.85),
    ("ledger:TOOL_EXEC", "TOOL", 0.7),
    ("ledger:MODEL", "MODEL", 0.7),
    ("ledger:MEMORY", "MEMORY", 0.7),
    ("health:import:", "ARCHITECTURE", 0.9),
    ("health:registry:", "ROUTING", 0.8),
    ("health:db:", "DATABASE", 0.8),
    ("health:pool:", "PROVIDER", 0.75),
    ("health:", "UNKNOWN", 0.3),
    ("storage:", "UNKNOWN", 0.2),
)

# Mots-clés signaux → capacités existantes candidates (existing-first explicite).
EXISTING_HINTS: Tuple[Tuple[str, str], ...] = (
    ("breaker:", "circuit_breaker+fallback_chain (core/routing)"),
    ("ledger:TOOL_EXEC", "ToolRegistry guard+timeout (core/agent/tools_registry)"),
    ("health:db:", "UnifiedMemoryGateway WAL+prune (core/memory)"),
    ("health:registry:", "CanonicalModelRegistry fallback chains (core/routing)"),
    ("health:pool:", "OllamaProvider local pool (core/providers)"),
    ("storage:", "prune 90j + auto-éviction cloud_guard (existant)"),
)


@dataclass(frozen=True)
class EvidenceBundle:
    component: str
    signals: Tuple[EvolutionSignal, ...]
    root_cause: str
    confidence: float


@dataclass(frozen=True)
class EvolutionProposal:
    proposal_id: str
    signal_ids: Tuple[str, ...]
    component: str
    root_cause: str
    confidence: float
    score: float
    verdict: Verdict
    reasons: Tuple[str, ...]
    risk: float
    cost: float
    recommended_change: str
    tests_required: Tuple[str, ...]
    benchmark_required: bool
    rollback_plan: str
    provenance: str
    state: OpportunityState = OpportunityState.PROPOSED


def _component_of(signal_id: str) -> str:
    head = signal_id.split(":", 1)
    if len(head) == 2:
        tail = head[1].split(".", 1)
        return f"{head[0]}:{tail[0]}"
    return signal_id


def correlate(signals: List[EvolutionSignal]) -> List[EvidenceBundle]:
    """Regroupe par composant ; symptomes corrélés = un seul faisceau."""
    groups: Dict[str, List[EvolutionSignal]] = {}
    for s in signals:
        groups.setdefault(_component_of(s.signal_id), []).append(s)
    bundles = []
    for component, items in sorted(groups.items()):
        cause, conf = "UNKNOWN", 0.2
        for prefix, cat, c in ROOT_CAUSE_MAP:
            if any(i.signal_id.startswith(prefix) for i in items):
                cause, conf = cat, c
                break
        conf = min(0.95, conf + 0.05 * (len(items) - 1))  # convergence relevée, bornée
        bundles.append(EvidenceBundle(component=component,
                                      signals=tuple(items),
                                      root_cause=cause, confidence=round(conf, 3)))
    return bundles


def check_existing(bundle: EvidenceBundle,
                   inventory: Collection[str]) -> Tuple[bool, str]:
    """Existing-first : le faisceau correspond-il à une capacité connue ?"""
    inv = {str(i) for i in inventory}
    for prefix, capability in EXISTING_HINTS:
        if any(s.signal_id.startswith(prefix) for s in bundle.signals):
            known = capability.split(" (")[0]
            if known in inv or not inv:
                return True, f"capacité existante : {capability}"
            return False, f"capacité requise absente d'inventaire : {capability}"
    return False, "aucune correspondance existing-first"


def fingerprint(bundle: EvidenceBundle, kind: str) -> str:
    raw = f"{bundle.component}|{bundle.root_cause}|{kind}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def suppress_duplicates(proposals: List[EvolutionProposal],
                        active_fingerprints: Collection[str]
                        ) -> Tuple[List[EvolutionProposal], int]:
    """Anti-tempête pure : un problème actif = une proposition."""
    active = set(active_fingerprints)
    kept, dropped = [], 0
    for p in proposals:
        if p.proposal_id in active:
            dropped += 1
            continue
        active.add(p.proposal_id)
        kept.append(p)
    return kept, dropped


def propose(bundle: EvidenceBundle, kind: str, recommended_change: str,
            inventory: Collection[str], recent_change_ids: Collection[str] = (),
            ) -> Tuple[EvolutionProposal, OpportunityDossier]:
    """Construit le dossier depuis le faisceau, décide, fige en PROPOSED."""
    if bundle.root_cause == "UNKNOWN":
        rc, conf = "", bundle.confidence
    else:
        rc, conf = bundle.root_cause, bundle.confidence
    worst = max((s.value for s in bundle.signals), default=0.0)
    sev = max((s.severity for s in bundle.signals), default="WATCH")
    existing_ok, existing_note = check_existing(bundle, inventory)
    self_gen = any((s.provenance or "").startswith("change:")
                   and s.provenance.split(":", 1)[1] in set(recent_change_ids)
                   for s in bundle.signals)
    dossier = OpportunityDossier(
        signal=",".join(sorted(s.signal_id for s in bundle.signals)),
        evidence_class=EvidenceClass.MEASURED_NOW,
        observation_time=",".join(sorted(str(s.timestamp) for s in bundle.signals)),
        source=",".join(sorted({s.source for s in bundle.signals})),
        current_value=worst, baseline=0.0,
        noise_floor=0.0 if sev in ("ANOMALY", "REGRESSION", "CRITICAL") else 1.0,
        confidence=conf, impact=8.0 if sev == "CRITICAL" else 5.0,
        root_cause=rc, value=6.0 if rc else 0.0,
        risk=7.0 if sev == "CRITICAL" else 3.0, cost=3.0, complexity=3.0,
        reversibility=8.0, existing_capability_checked=existing_ok,
    )
    verdict = Verdict.DEFER
    if self_gen and sev != "CRITICAL":
        reasons = ["self_generated_signal: transitoire post-changement attendu"]
    else:
        verdict, reasons = decide(dossier)
    reasons = tuple([existing_note] + list(reasons))
    proposal = EvolutionProposal(
        proposal_id=fingerprint(bundle, kind),
        signal_ids=tuple(sorted(s.signal_id for s in bundle.signals)),
        component=bundle.component, root_cause=bundle.root_cause or "UNKNOWN",
        confidence=conf, score=0.0, verdict=verdict, reasons=reasons,
        risk=dossier.risk, cost=dossier.cost,
        recommended_change=recommended_change,
        tests_required=("targeted", "contracts", "confinement"),
        benchmark_required=(verdict == Verdict.IMPLEMENT),
        rollback_plan="retrait du changement, rescan, ledger",
        provenance=",".join(sorted({s.source for s in bundle.signals})),
    )
    return proposal, dossier
