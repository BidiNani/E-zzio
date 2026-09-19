"""Tissu de connaissance : intention, normalisation, dédup, fraîcheur,
confiance par preuves, conflits déclarés, grille qualité, UNTRUSTED."""
import pytest

from core.capabilities.research_fabric import (
    Breadth,
    Confidence,
    Freshness,
    SearchIntent,
    SourceResult,
    classify_search,
    confidence_of,
    deduplicate,
    detect_conflict,
    freshness_of,
    mark_untrusted,
    normalize_results,
    quality_gate,
    save_research_session,
)


def test_classify_search_intents():
    assert classify_search("Quoi de neuf aujourd'hui sur l'IA ?")[0] == SearchIntent.NEWS
    assert classify_search("Fais-moi une étude complète de X")[1] == Breadth.DEEP
    assert classify_search("Trouve absolument toutes les infos")[1] == Breadth.MAX
    assert classify_search("Compare A versus B")[0] == SearchIntent.COMPARISON
    assert classify_search("Surveille ce dépôt")[0] == SearchIntent.MONITORING
    i, b, r = classify_search("truc vague")
    assert (i, b) == (SearchIntent.RESEARCH, Breadth.NORMAL)
    assert any("LOW" in x for x in r)


def test_normalize_tolerant():
    items = [
        {"title": "A", "url": "https://ex.com/a?utm_source=x", "content": "c1"},
        {"title": "B", "link": "https://ex.com/b", "snippet": "c2",
         "published_date": "bad-date"},
        {"no_url": True},
        "junk",
    ]
    out = normalize_results("tavily", items, query="q", now=9.0)
    assert len(out) == 2  # sans locator ignoré, junk ignoré
    assert out[0].provenance == "query=q" and out[0].retrieved_at == 9.0
    assert out[1].published_at is None  # date invalide → None, pas d'invention


def test_dedup_honest_counts():
    def mk(loc, c):
        return SourceResult("t", "t", loc, c)
    res, stats = deduplicate([
        mk("https://a.com/x?utm_source=1", "same"),
        mk("https://a.com/x", "same"),  # doublon exact
        mk("https://a.com/x", "different"),  # même page, contenu différent
        mk("https://b.org/y", "same"),  # même texte, origine indépendante
    ])
    assert stats == {"pages": 4, "distinct": 3, "independent_origins": 2}
    assert len(res) == 3


def test_freshness_contextual():
    now = 1_757_000_000.0
    assert freshness_of(None, now) == Freshness.UNKNOWN
    assert freshness_of(now - 86400, now) == Freshness.FRESH
    assert freshness_of(now - 20 * 86400, now) == Freshness.RECENT
    assert freshness_of(now - 200 * 86400, now) == Freshness.STALE
    assert freshness_of(now - 500 * 86400, now) == Freshness.HISTORICAL
    # Sujet historique : volatilité 10 ans → 2 ans reste RECENT
    assert freshness_of(now - 730 * 86400, now,
                        volatility_days=3650) == Freshness.RECENT


def test_confidence_from_counts():
    assert confidence_of(0, False, False, True) == Confidence.INSUFFICIENT
    assert confidence_of(1, False, False, True) == Confidence.LOW
    assert confidence_of(3, True, False, True) == Confidence.HIGH
    assert confidence_of(3, False, False, True) == Confidence.MEDIUM
    assert confidence_of(5, True, True, True) == Confidence.CONFLICTED


def test_conflict_requires_independent_origins():
    assert detect_conflict([("k", "s1", 1), ("k", "s2", -1)]) == ["k"]
    assert detect_conflict([("k", "s1", 1), ("k", "s2", 1)]) == []
    assert detect_conflict([("k", "s1", 1)]) == []  # une voix ≠ conflit


def test_quality_gate_lists_gaps():
    status, missing = quality_gate(3, True, True, True, True, True)
    assert (status, missing) == ("COMPLETE", [])
    status, missing = quality_gate(1, False, False, False, False, False)
    assert status == "INCOMPLETE" and len(missing) == 6


def test_mark_untrusted_envelope():
    from core.security.untrusted import BEGIN
    r = SourceResult("t", "T", "https://x.y/z", "contenu externe <x>")
    out = mark_untrusted([r])
    assert BEGIN in out[0]["content"]
    assert out[0]["provenance"] == "" or isinstance(out[0]["provenance"], str)
    assert out[0]["trust"] == "UNKNOWN"


@pytest.mark.asyncio
async def test_research_session_reuses_gateway(tmp_path):
    from core.memory.unified_gateway import UnifiedMemoryGateway
    gw = UnifiedMemoryGateway(db_path=str(tmp_path / "r.db"))
    await gw.init()
    await save_research_session(gw, "proj-x", "veille IA",
                                "3 origines indépendantes",
                                ["https://a.com/1", "https://b.org/2"])
    hist = await gw.get_session_history(session_id="proj-x", limit=10)
    assert len(hist) == 1 and "veille IA" in hist[0]["content"]
