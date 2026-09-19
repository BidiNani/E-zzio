"""Preuves sémantiques — alignement déterministe, sans NLP simulé.

Responsabilité unique (nouveau module justifié : aucun existant n'aligne
entités/portées/temps) : décider si deux claims parlent du même fait et
quelle relation les lie. Tout est lexical et numérique, étiqueté comme tel :
- entités : normalisation unicode/casse/espaces (pas de résolution NLP) ;
- temps : published_at comparés par fenêtres, UNKNOWN → jamais de
  contradiction affirmée ;
- mesures : regex nombre+unité ; même entité+unité+fenêtre temporelle mais
  valeurs différentes → CONTRADICTS candidat, sinon TEMPORAL_DIFFERENCE ;
- copies : même hash contenu → DERIVED_FROM (1 groupe de preuve) ;
- recouvrement lexical (Jaccard) → regroupement lexical, pas sémantique.

Relations : SUPPORTS, CONTRADICTS, PARTIAL_SUPPORT, SAME_EVENT,
DIFFERENT_SCOPE, DERIVED_FROM, UNKNOWN. Graphe léger en mémoire (dict).
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum


class SemRelation(StrEnum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    PARTIAL_SUPPORT = "PARTIAL_SUPPORT"
    SAME_EVENT = "SAME_EVENT"
    DIFFERENT_SCOPE = "DIFFERENT_SCOPE"
    DERIVED_FROM = "DERIVED_FROM"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Measurement:
    value: float
    unit: str
    span: str  # texte brut autour, pour traçabilité


_MEASURE_RE = re.compile(
    r"(?P<sign>[-−+]?)\s*(?P<num>\d+(?:[.,]\d+)?(?:[eE][+-]?\d+)?)\s*(?P<unit>millions?|milliards?|EUR|USD|"
    r"dollars?|euros?|livres?|£|yens?|¥|CHF|CAD|AUD|GBP|JPY|CNY|"
    r"tonnes?|litres?|watts?|habitants?|"
    r"utilisateurs?|users?|degrés?|secondes?|seconds?|sec|minutes?|mins?|min|hours?|heures?|"
    r"cm|mm|km|ms|MB|GB|TB|kg|"
    r"(?-i:m)(?![a-zà-ÿ])|g(?![a-zà-ÿ])|s(?![a-zà-ÿ])|h(?![a-zà-ÿ])|"
    r"Go|Mo|ans?|jours?|€|\$|%|pour\s*cents?|"
    r"v\d+(?:\.\d+)+|\d+(?:\.\d+)+)(?![a-zà-ÿ])",
    re.IGNORECASE)

# Familles d'unités convertibles déterministiquement (facteur → canonique).
# Temps uniquement : conversions incontestables (§18). Devises : JAMAIS
# converties sans taux (UNSUPORTED par défaut).
_TIME_FACTORS = {
    "ms": 0.001,
    "s": 1.0, "sec": 1.0, "secondes": 1.0, "second": 1.0, "seconds": 1.0,
    "min": 60.0, "mins": 60.0, "minute": 60.0, "minutes": 60.0,
    "h": 3600.0, "hour": 3600.0, "hours": 3600.0, "heure": 3600.0,
    "heures": 3600.0,
}


def canonical_time(value: float, unit: str):
    """(secondes,) ou None si hors famille temps."""
    f = _TIME_FACTORS.get((unit or "").lower())
    return value * f if f is not None else None


# Échelles de comptage : k=1e3, million=1e6, milliard/billion=1e9.
# Comparaison canonique uniquement entre mots d'échelle (jamais avec
# mètres/monnaies : familles distinctes).
_COUNT_FACTORS = {
    "k": 1e3,
    "million": 1e6, "millions": 1e6,
    "milliard": 1e9, "milliards": 1e9, "billion": 1e9, "billions": 1e9,
    "bn": 1e9,
}


def canonical_count(value: float, unit: str):
    """(compte canonique,) ou None si hors famille échelle."""
    f = _COUNT_FACTORS.get((unit or "").lower())
    return value * f if f is not None else None

_CURRENCY_TOKENS = ("€", "$", "eur", "usd", "dollar", "euro", "livre", "yen")


def normalize_entity(text: str) -> str:
    """Minuscules, sans accents, espaces condensés, ponctuation retirée."""
    t = unicodedata.normalize("NFKD", text or "").lower()
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def extract_measurements(text: str) -> list[Measurement]:
    """Nombres + unités explicites, signe inclus. Sans unité → ignoré."""
    out = []
    for m in _MEASURE_RE.finditer(text or ""):
        try:
            val = float((m.group("sign") or "") + m.group("num").replace(",", "."))
        except ValueError:
            continue
        out.append(Measurement(value=val, unit=m.group("unit").lower(),
                               span=(m.group("sign") or "") + m.group(0)[len(m.group("sign") or ""):][:40]))
    return out


_SCALE_WORDS = (
    (r"(?P<n>\d+(?:[.,]\d+)?)\s*(?:milliards?|billions?|bn|Mds?)\b", 1e9),
    (r"(?P<n>\d+(?:[.,]\d+)?)\s*(?:millions?|(?-i:M)\b)", 1e6),
    (r"(?P<n>\d+(?:[.,]\d+)?)\s*[kK]\b", 1e3),
)


def expand_scales(text: str) -> str:
    """Mots d'échelle → valeur canonique (comparaison uniquement).
    'm' minuscule seul (mètre) jamais expansé."""
    out = text or ""
    for pat, mult in _SCALE_WORDS:
        def _rep(mm: re.Match[str], _mult: float = mult) -> str:
            try:
                v = float(mm.group("n").replace(",", "."))
            except ValueError:
                return mm.group(0)
            return str(int(v * _mult)) if (v * _mult).is_integer() else str(v * _mult)
        out = re.sub(pat, _rep, out)
    return out


def content_fingerprint(text: str) -> str:
    return hashlib.sha1(normalize_entity(text).encode("utf-8")).hexdigest()[:16]


def lexical_overlap(a: str, b: str) -> float:
    """Jaccard sur tokens normalisés. Lexical, étiqueté comme tel."""
    ta, tb = set(normalize_entity(a).split()), set(normalize_entity(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def same_timeframe(pub_a: float | None, pub_b: float | None,
                   window_days: float = 7.0) -> bool | None:
    """True/False si les deux dates connues, None si inconnue (→ UNKNOWN)."""
    if not pub_a or not pub_b or pub_a <= 0 or pub_b <= 0:
        return None
    return abs(pub_a - pub_b) <= window_days * 86400.0


@dataclass
class EvidenceNode:
    claim_id: str
    text: str
    origin: str  # domaine
    published_at: float | None = None
    measurements: list[Measurement] = field(default_factory=list)


@dataclass(frozen=True)
class EvidenceEdge:
    left: str
    right: str
    relation: SemRelation
    reason: str


def relate(a: EvidenceNode, b: EvidenceNode) -> EvidenceEdge:
    """Relation entre deux claims. Doute temporel → jamais CONTRADICTS."""
    if a.claim_id == b.claim_id:
        return EvidenceEdge(a.claim_id, b.claim_id, SemRelation.SAME_EVENT,
                            "même claim")
    if (content_fingerprint(a.text) == content_fingerprint(b.text)
            and a.origin != b.origin):
        return EvidenceEdge(a.claim_id, b.claim_id, SemRelation.DERIVED_FROM,
                            "même contenu, hôtes distincts : miroir/copie")
    # Mesures : même unité + contextes lexicaux proches.
    for ma in a.measurements:
        for mb in b.measurements:
            if ma.unit != mb.unit:
                continue
            if lexical_overlap(a.text, b.text) < 0.25:
                continue
            tf = same_timeframe(a.published_at, b.published_at)
            if ma.value == mb.value:
                return EvidenceEdge(a.claim_id, b.claim_id,
                                    SemRelation.SUPPORTS,
                                    f"même mesure {ma.span}")
            if tf is False:
                return EvidenceEdge(a.claim_id, b.claim_id,
                                    SemRelation.DIFFERENT_SCOPE,
                                    "valeurs distinctes à dates distinctes : "
                                    "différence temporelle, pas contradiction")
            if tf is None:
                return EvidenceEdge(a.claim_id, b.claim_id, SemRelation.UNKNOWN,
                                    "dates inconnues : contradiction non décidable")
            return EvidenceEdge(a.claim_id, b.claim_id,
                                SemRelation.CONTRADICTS,
                                f"{ma.span} vs {mb.span}, même fenêtre")
    ov = lexical_overlap(a.text, b.text)
    if ov >= 0.6:
        tf = same_timeframe(a.published_at, b.published_at)
        if tf is False:
            return EvidenceEdge(a.claim_id, b.claim_id,
                                SemRelation.DIFFERENT_SCOPE,
                                "fort recouvrement lexical, dates distinctes")
        return EvidenceEdge(a.claim_id, b.claim_id, SemRelation.SAME_EVENT,
                            f"recouvrement lexical {ov:.2f}")
    if ov >= 0.3:
        return EvidenceEdge(a.claim_id, b.claim_id,
                            SemRelation.PARTIAL_SUPPORT,
                            f"recouvrement partiel {ov:.2f}")
    return EvidenceEdge(a.claim_id, b.claim_id, SemRelation.UNKNOWN,
                        f"recouvrement {ov:.2f} : relation indécidable")


def build_graph(nodes: list[EvidenceNode]) -> tuple[list[EvidenceNode],
                                                     list[EvidenceEdge]]:
    """Graphe léger : toutes les paires (borné par l'appelant via budgets)."""
    edges = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            edges.append(relate(nodes[i], nodes[j]))
    return nodes, edges


def contradiction_stances(edges: list[EvidenceEdge],
                          origin_of: dict[str, str]) -> list[tuple[str, str, int]]:
    """Arêtes CONTRADICTS → positions déclarées (clé, origine, ±1) pour le
    detect_conflict existant. Une seule autorité de conflit."""
    stances = []
    for e in edges:
        if e.relation == SemRelation.CONTRADICTS:
            key = f"num:{e.left}<>{e.right}"
            stances.append((key, origin_of.get(e.left, "?"), 1))
            stances.append((key, origin_of.get(e.right, "?"), -1))
    return stances


def evidence_groups(nodes: list[EvidenceNode],
                    edges: list[EvidenceEdge]) -> list[list[str]]:
    """Regroupe les nœuds liés par DERIVED_FROM/SAME_EVENT : 1 groupe =
    1 preuve (copies et miroirs jamais comptés comme confirmations)."""
    parent = {n.claim_id: n.claim_id for n in nodes}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for e in edges:
        if e.relation in (SemRelation.DERIVED_FROM, SemRelation.SAME_EVENT):
            a, b = find(e.left), find(e.right)
            parent[a] = b
    groups: dict[str, list[str]] = {}
    for n in nodes:
        groups.setdefault(find(n.claim_id), []).append(n.claim_id)
    return sorted(groups.values(), key=len, reverse=True)
