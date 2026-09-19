"""Tissu de connaissance — fédération et normalisation, pas de stockage.

MANY SOURCES → ONE QUERY MODEL → ONE EVIDENCE MODEL → ONE PROVENANCE MODEL.
Tout est pur et déterministe sauf save_research_session (gateway existant).
Aucune extraction NLP simulée : les conflits naissent d'oppositions déclarées,
la confiance naît de comptages réels, jamais de pourcentages inventés.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from urllib.parse import urlparse


class SearchIntent(StrEnum):
    FACT_LOOKUP = "FACT_LOOKUP"
    NEWS = "NEWS"
    RESEARCH = "RESEARCH"
    COMPARISON = "COMPARISON"
    MONITORING = "MONITORING"
    TECHNICAL = "TECHNICAL"


class Breadth(StrEnum):
    QUICK = "QUICK"
    NORMAL = "NORMAL"
    DEEP = "DEEP"
    MAX = "MAX"


class Trust(StrEnum):
    OFFICIAL = "OFFICIAL"
    PRIMARY = "PRIMARY"
    REPUTABLE_SECONDARY = "REPUTABLE_SECONDARY"
    COMMUNITY = "COMMUNITY"
    UNVERIFIED = "UNVERIFIED"
    UNKNOWN = "UNKNOWN"
    UNTRUSTED = "UNTRUSTED"


class Freshness(StrEnum):
    FRESH = "FRESH"
    RECENT = "RECENT"
    STALE = "STALE"
    HISTORICAL = "HISTORICAL"
    UNKNOWN = "UNKNOWN"


class Confidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    CONFLICTED = "CONFLICTED"
    INSUFFICIENT = "INSUFFICIENT"
    UNKNOWN = "UNKNOWN"


_INTENT_KEYWORDS: tuple[tuple[SearchIntent, tuple[str, ...]], ...] = (
    (SearchIntent.MONITORING, ("surveille", "monitor", "watch", "alerte", "suivi")),
    (SearchIntent.NEWS, ("news", "nouvelles", "actualité", "actualités", "dernières",
                         "aujourd'hui", "hier", "breaking", "veille")),
    (SearchIntent.COMPARISON, ("compare", "comparer", "comparaison", "versus", "vs ",
                               "différence", "quel est le meilleur")),
    (SearchIntent.TECHNICAL, ("documentation", "api", "error", "erreur", "stacktrace",
                              "comment implémenter", "tutorial", "tutoriel")),
    (SearchIntent.FACT_LOOKUP, ("qui est", "qu'est-ce que", "quelle est la capitale",
                                "combien", "quand", "what is", "who is", "define")),
)

_BREADTH_KEYWORDS: tuple[tuple[Breadth, tuple[str, ...]], ...] = (
    (Breadth.QUICK, ("vite", "rapidement", "quick", "bref", "en deux mots")),
    (Breadth.DEEP, ("complète", "approfondie", "étude", "complète", "détaillée",
                     "deep", "thorough")),
    (Breadth.MAX, ("absolument tout", "maximum", "exhaustif", "toutes les",
                    "max coverage", "tout ce qui existe")),
)


def classify_search(text: str) -> tuple[SearchIntent, Breadth, list[str]]:
    """Intention + profondeur. Inconnu → (RESEARCH, QUICK, confiance basse)."""
    t = (text or "").lower()
    intent, breadth, reasons = SearchIntent.RESEARCH, Breadth.NORMAL, ["défaut"]
    for cand, words in _INTENT_KEYWORDS:
        if any(w in t for w in words):
            intent = cand
            reasons = [f"intent={cand.value}"]
            break
    for cand, words in _BREADTH_KEYWORDS:
        if any(w in t for w in words):
            breadth = cand
            reasons.append(f"breadth={cand.value}")
            break
    else:
        if intent == SearchIntent.NEWS:
            breadth = Breadth.QUICK
            reasons.append("news→QUICK")
    if intent == SearchIntent.RESEARCH and breadth == Breadth.NORMAL:
        reasons = ["aucun marqueur: RESEARCH/NORMAL, confiance LOW"]
    return intent, breadth, reasons


@dataclass(frozen=True)
class SourceResult:
    source_id: str  # ex: tavily, searxng, github, internal
    title: str
    locator: str  # url ou chemin
    content: str
    retrieved_at: float = 0.0
    published_at: float | None = None
    trust: Trust = Trust.UNKNOWN
    provenance: str = ""  # requête d'origine + date de collecte


def _parse_pub_date(pub: Any) -> float | None:
    """Timestamp, ISO-8601 ou date simple → epoch. Échec → None (UNKNOWN)."""
    if pub is None:
        return None
    try:
        return float(pub)
    except (TypeError, ValueError):
        pass
    try:
        from datetime import datetime
        txt = str(pub).strip().replace("Z", "+00:00")
        return datetime.fromisoformat(txt).timestamp()
    except (ValueError, OverflowError):
        return None


def _clean_locator(url: str) -> str:
    loc = (url or "").strip().lower().rstrip("/")
    for junk in ("?utm_source=", "&utm_source=", "?utm_medium=", "&utm_medium=",
                 "?utm_campaign=", "&utm_campaign="):
        cut = loc.find(junk)
        if cut != -1:
            loc = loc[:cut]
    return loc


def normalize_results(provider: str, items: list[dict[str, Any]],
                      query: str = "", now: float = 0.0) -> list[SourceResult]:
    """Formes tavily/searxng/génériques → SourceResult. Pure et tolérante."""
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        locator = str(it.get("url") or it.get("link") or it.get("locator") or "")
        if not locator:
            continue
        pub = it.get("published_at") or it.get("published_date") or it.get("date")
        pub_f = _parse_pub_date(pub)
        out.append(SourceResult(
            source_id=str(it.get("source_id") or provider),
            title=str(it.get("title") or locator)[:200],
            locator=locator,
            content=str(it.get("content") or it.get("snippet") or it.get("text") or ""),
            retrieved_at=now,
            published_at=pub_f,
            provenance=f"query={query[:120]}",
        ))
    return out


def origin_domain(locator: str) -> str:
    try:
        host = urlparse(locator).netloc.lower()
    except ValueError:
        return locator.lower()
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def deduplicate(results: list[SourceResult]) -> tuple[list[SourceResult], dict[str, int]]:
    """Déduplique (locator nettoyé + hash contenu). Retourne (uniques, stats
    honnêtes : pages, documents distincts, origines indépendantes)."""
    seen, unique = set(), []
    for r in results:
        key = (_clean_locator(r.locator),
               hashlib.sha1(r.content.encode("utf-8", "replace")).hexdigest()[:12])
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    origins = {origin_domain(r.locator) for r in unique}
    return unique, {"pages": len(results), "distinct": len(unique),
                    "independent_origins": len(origins)}


def freshness_of(published_at: float | None, now: float,
                 volatility_days: float = 30.0) -> Freshness:
    """Fraîcheur contextuelle : la volatilité du sujet donne l'échelle."""
    if not published_at or published_at <= 0:
        return Freshness.UNKNOWN
    age_days = max((now - published_at) / 86400.0, 0.0)
    if age_days <= volatility_days / 10:
        return Freshness.FRESH
    if age_days <= volatility_days:
        return Freshness.RECENT
    if age_days <= volatility_days * 12:
        return Freshness.STALE
    return Freshness.HISTORICAL


def confidence_of(n_independent: int, corroborated: bool, conflicts: bool,
                  freshness_ok: bool) -> Confidence:
    """Confiance par comptages réels. Jamais de pourcentage, jamais 100%."""
    if conflicts:
        return Confidence.CONFLICTED
    if n_independent <= 0:
        return Confidence.INSUFFICIENT
    if n_independent == 1:
        return Confidence.LOW
    if corroborated and freshness_ok:
        return Confidence.HIGH
    return Confidence.MEDIUM


def detect_conflict(stances: list[tuple[str, str, int]]) -> list[str]:
    """Oppositions déclarées (clé, source, +1/-1/0) → clés en CONFLIT.

    Aucune NLP : l'appelant fournit les positions. Origines distinctes exigées.
    """
    by_key: dict[str, dict[str, int]] = {}
    for key, source, stance in stances:
        by_key.setdefault(key, {})[source] = stance
    conflicts = []
    for key, votes in by_key.items():
        vals = set(votes.values())
        if len(votes) >= 2 and 1 in vals and -1 in vals:
            conflicts.append(key)
    return sorted(conflicts)


def quality_gate(n_independent: int, has_primary: bool, freshness_ok: bool,
                 conflicts_checked: bool, traced: bool,
                 uncertainty_explicit: bool) -> tuple[str, list[str]]:
    """Grille §47 : COMPLETE ou INCOMPLETE + manques explicites."""
    missing = []
    if n_independent < 2:
        missing.append("coverage<2 origines indépendantes")
    if not has_primary:
        missing.append("source primaire absente")
    if not freshness_ok:
        missing.append("fraîcheur insuffisante")
    if not conflicts_checked:
        missing.append("contradictions non vérifiées")
    if not traced:
        missing.append("claims non traçables")
    if not uncertainty_explicit:
        missing.append("incertitude non explicite")
    return ("COMPLETE", []) if not missing else ("INCOMPLETE", missing)


def mark_untrusted(results: list[SourceResult]) -> list[dict[str, Any]]:
    """Enveloppe UNTRUSTED + provenance avant tout contexte modèle."""
    from core.security.untrusted import wrap_untrusted

    return [{
        "title": r.title, "locator": r.locator,
        "content": wrap_untrusted(r.content),
        "trust": r.trust.value, "provenance": r.provenance,
        "published_at": r.published_at,
    } for r in results]


async def save_research_session(gateway, session_id: str, query: str,
                                summary: str, locators: list[str]) -> None:
    """Mémorise une session de recherche via le gateway existant (0 nouveau store)."""
    content = (f"[RESEARCH] query={query[:200]} | "
               f"sources={len(locators)} | {summary[:500]} | "
               f"locators={', '.join(locators[:10])}")
    await gateway.record_message(session_id, "assistant", content,
                                 metadata={"kind": "RESEARCH_SESSION"})
