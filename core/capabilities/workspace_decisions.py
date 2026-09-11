"""Décisions workspace — pures, bornées, gouvernées par les autorités existantes.

Couvre ce qui manque réellement : BEST NEXT ACTION, BEST SOURCE NEXT
(valeur d'information), ordre internal-first, feedback→signal qualité,
stall assessment, gap report, plan source (modes du DecisionRouter existant).
NE choisit jamais : modèle (registry), provider d'exécution (router),
agent au-delà de select_worker_for_intent (fleet), policy (policy).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from core.capabilities.research_fabric import Breadth, SearchIntent
from core.decision_router import SearchMode


class NextAction(str, Enum):
    ANSWER = "ANSWER"
    ASK = "ASK"
    SEARCH = "SEARCH"
    MEASURE = "MEASURE"
    DELEGATE = "DELEGATE"
    WAIT = "WAIT"
    CANCEL = "CANCEL"
    ESCALATE = "ESCALATE"


class StallVerdict(str, Enum):
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    STALLED = "STALLED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DecisionState:
    has_answer: bool = False
    ambiguous: bool = False
    needs_external_info: bool = False
    needs_observation: bool = False
    needs_specialist: bool = False
    waiting_on: str = ""
    cancel_requested: bool = False
    blocked_on_policy: bool = False
    risk_high: bool = False


def best_next_action(s: DecisionState) -> Tuple[NextAction, str]:
    """Priorité : sécurité > annulation > clarification > mesure > délégation."""
    if s.blocked_on_policy or s.risk_high:
        return NextAction.ESCALATE, "policy/risque : escalade"
    if s.cancel_requested:
        return NextAction.CANCEL, "annulation explicite"
    if s.ambiguous and not s.has_answer:
        return NextAction.ASK, "ambiguïté sans réponse"
    if s.needs_observation:
        return NextAction.MEASURE, "observation peu coûteuse d'abord"
    if s.needs_specialist:
        return NextAction.DELEGATE, "spécialiste requis"
    if s.needs_external_info:
        return NextAction.SEARCH, "information externe requise"
    if s.waiting_on:
        return NextAction.WAIT, f"attente : {s.waiting_on}"
    if s.has_answer:
        return NextAction.ANSWER, "réponse disponible"
    return NextAction.ASK, "aucune voie : clarifier"


@dataclass(frozen=True)
class SourceCandidate:
    source_id: str
    expected_value: float = 0.0  # 0..10 réduction d'incertitude estimée
    cost: float = 0.0  # 0..10 (quota, latence, prix)
    already_covered: bool = False


def best_source_next(candidates: List[SourceCandidate]) -> Optional[str]:
    """Valeur d'information par coût. Couvert ou coût nul→ ignoré ; vide → None."""
    best, best_ratio = None, 0.0
    for c in candidates:
        if c.already_covered or c.cost <= 0:
            continue
        ratio = c.expected_value / c.cost
        if ratio > best_ratio:
            best, best_ratio = c.source_id, ratio
    return best


def internal_first_order(has_internal_match: bool, freshness_required: bool
                         ) -> List[str]:
    """INTERNAL-FIRST quand pertinent, EXTERNAL pour validation/fraîcheur."""
    if has_internal_match and not freshness_required:
        return ["internal"]
    if has_internal_match:
        return ["internal", "external"]
    return ["external"]


_FEEDBACK_SIGNALS: Tuple[Tuple[str, str], ...] = (
    ("c'est faux", "answer_incorrect"),
    ("pas ce que je voulais", "intent_mismatch"),
    ("mauvaise source", "source_bad"),
    ("incomplet", "answer_incomplete"),
    ("trop lent", "latency_bad"),
    ("trop cher", "cost_bad"),
)


def feedback_to_signal(text: str, task_id: str = "",
                       model: str = "") -> Optional[Dict[str, str]]:
    """Retour utilisateur → signal qualité pour la boucle d'évolution."""
    t = (text or "").lower()
    for marker, kind in _FEEDBACK_SIGNALS:
        if marker in t:
            return {"signal_id": f"feedback:{kind}", "source": "user",
                    "task_id": task_id, "model": model}
    return None


def assess_stall(state: str, last_event_age_s: Optional[float],
                 timeout_s: float, waiting_label: str = "") -> StallVerdict:
    """État + âge du dernier événement → verdict. Âge inconnu → UNKNOWN."""
    s = (state or "").upper()
    if s in ("SUCCEEDED", "COMPLETED", "FAILED", "CANCELLED", "ROLLED_BACK"):
        return StallVerdict.RUNNING  # terminaux : rien à détecter
    if last_event_age_s is None:
        return StallVerdict.UNKNOWN
    if waiting_label or "WAIT" in s:
        return StallVerdict.WAITING
    if last_event_age_s > timeout_s:
        return StallVerdict.STALLED
    return StallVerdict.RUNNING


_BREADTH_MODE: Dict[Breadth, SearchMode] = {
    Breadth.QUICK: SearchMode.FAST,
    Breadth.NORMAL: SearchMode.RESEARCH,
    Breadth.DEEP: SearchMode.FORENSIC,
    Breadth.MAX: SearchMode.FORENSIC,
}

_BREADTH_BUDGET: Dict[Breadth, Dict[str, int]] = {
    Breadth.QUICK: {"max_results": 3, "max_providers": 1, "timeout_s": 20},
    Breadth.NORMAL: {"max_results": 5, "max_providers": 2, "timeout_s": 45},
    Breadth.DEEP: {"max_results": 8, "max_providers": 3, "timeout_s": 120},
    Breadth.MAX: {"max_results": 10, "max_providers": 3, "timeout_s": 300},
}


def source_plan(intent: SearchIntent, breadth: Breadth) -> Dict[str, object]:
    """Plan : mode du DecisionRouter existant + budgets bornés (MAX ≠ illimité)."""
    return {"mode": _BREADTH_MODE[breadth].value,
            "budget": dict(_BREADTH_BUDGET[breadth]),
            "intent": intent.value}


def gap_report(known: List[str], missing: List[str], conflicted: List[str],
               verify: List[str]) -> Dict[str, List[str]]:
    """WHAT WE KNOW / DON'T KNOW / CONFLICTED / VERIFY — depuis fabric."""
    return {"known": list(known), "unknown": list(missing),
            "conflicted": list(conflicted), "to_verify": list(verify)}
