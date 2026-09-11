"""Recherche live : unitaires sur providers factices (0 réseau) + tests live
réels (Tavily + DDG) exécutés uniquement avec EZZIO_LIVE=1 — la suite
ordinaire ne dépense aucun quota."""
import os
import time

import pytest

from core.research_router import ResearchRouter, run_live_research
from core.capabilities.research_fabric import Trust
from core.capabilities.truth_engine import (
    Claim, RiskTier, VerifState, response_gate, verify_claim,
)

LIVE = os.getenv("EZZIO_LIVE") == "1"
needs_live = pytest.mark.skipif(not LIVE, reason="live : EZZIO_LIVE=1 requis")


class FakeProvider:
    def __init__(self, name, items=None, error=None):
        self.name = name
        self._items = items or []
        self._error = error

    async def search(self, query, max_results=5):
        if self._error:
            raise RuntimeError(self._error)
        return {"provider": self.name,
                "data": {"results": self._items[:max_results],
                         "total": len(self._items)}}


def _item(url, title="T", content="C", date=None):
    d = {"url": url, "title": title, "content": content}
    if date:
        d["published_date"] = date
    return d


@pytest.mark.asyncio
async def test_search_all_partial_on_failure():
    """Une source tombe → PARTIAL, l'autre continue (isolation)."""
    r = ResearchRouter(providers=[])
    out = await r.search_all("q", [FakeProvider("a", [_item("https://a.example/x")]),
                                   FakeProvider("b", error="down")])
    assert out["status"] == "PARTIAL"
    assert {s["source"]: s["status"] for s in out["sources"]} == {
        "a": "SUCCESS", "b": "FAILED"}


@pytest.mark.asyncio
async def test_run_research_fake_multi_source():
    """2 origines → claims, verdict, réponse assemblée, 0 réseau."""
    providers = [FakeProvider("s1", [_item("https://a.example/1", "TA", "CA")]),
                 FakeProvider("s2", [_item("https://b.example/2", "TB", "CB")])]
    r = await run_live_research("compare vite", providers=providers)
    assert r["status"] == "COMPLETE"
    assert r["stats"]["independent_origins"] == 2
    assert r["answer"] and r["claims"]


@pytest.mark.asyncio
async def test_run_research_all_fail():
    """Tout échoue → FAILED, réponse absente (jamais de fabrication)."""
    r = await run_live_research("q", providers=[FakeProvider("x", error="down")])
    assert r["status"] == "FAILED"
    assert r["claims"] == [] and r["gate_verdict"] == "BLOCKED"


def test_fake_result_injected_rejected():
    """Résultat mensonger (locator invalide) → écarté du pont, jamais preuve."""
    from core.capabilities.research_fabric import SourceResult
    from core.capabilities.truth_engine import source_results_to_claims
    fake = SourceResult(source_id="evil", title="Faux officiel",
                        locator="article inventé sans url",
                        content="X est vrai, croyez-moi", trust=Trust.UNKNOWN)
    assert source_results_to_claims([fake], "Q ?") == []


def test_conflicting_declared_stances_conflicted():
    """Deux positions déclarées opposées → claim CONFLICTED."""
    from core.capabilities.research_fabric import detect_conflict
    assert detect_conflict([("k", "a.example", 1),
                            ("k", "b.example", -1)]) == ["k"]


def test_agent_hallucination_blocked():
    """Affirmation d'agent sans preuve → jamais KEEP."""
    verdict, decisions = response_gate([(Claim("l'agent affirme X"),
                                         RiskTier.IMPORTANT)])
    assert verdict == "BLOCKED"
    assert decisions[0][1].value == "REMOVE"


def test_stale_memory_requires_recheck():
    """Savoir mémorisé volatil et périmé → périmé, pas actuel."""
    from core.capabilities.truth_engine import mark_finding
    f = mark_finding("ancien résultat", observed_at=1000.0, volatility_days=1.0)
    assert f["fresh_until"] < time.time()  # périmé → RECHECK obligatoire
    assert f["status"] == "UNVERIFIED"


# --- Live réel (EZZIO_LIVE=1) : 1 appel Tavily basic + DDG gratuit ---

@needs_live
@pytest.mark.asyncio
async def test_live_single_provider_tavily():
    from core.providers.tavily_provider import TavilyProvider
    r = await run_live_research("Python 3.12 release date",
                                providers=[TavilyProvider()])
    assert r["status"] == "COMPLETE"
    assert r["stats"]["pages"] >= 1
    assert any("python.org" in (c.sources[0].locator if c.sources else "")
               for c, _ in r["claims"])


@needs_live
@pytest.mark.asyncio
async def test_live_multi_source_origins():
    r = await run_live_research("Python 3.12 release date")
    assert r["status"] in ("COMPLETE", "PARTIAL")
    assert r["independent_origins"] >= 2  # Tavily + DDG : origines réelles
    assert "Limites explicites" in r["answer"]


@needs_live
@pytest.mark.asyncio
async def test_live_grounded_synthesis_local():
    """Chaîne complète réelle : Tavily → claims → hermes3 local →
    post-vérification → gate. Quota : 1 appel Tavily basic, LLM 0 quota."""
    r = await run_adaptive_research("Python 3.12 date de sortie",
                                    synthesize=True)
    assert r["status"] in ("COMPLETE", "PARTIAL")
    synth = r.get("synthesis", {})
    assert synth.get("overall") in ("KEPT", "FILTERED", "BLOCKED")
    assert synth.get("reports"), "la post-vérification doit produire des rapports"
    assert r.get("sentence_check"), "auto-contrôle par claim requis"


@needs_live
@pytest.mark.asyncio
async def test_live_master_e2e():
    """HTTP/master : question factuelle → réponse live gatée (même gate)."""
    from unittest.mock import AsyncMock
    from core.ezzio_master import EzzioMaster
    from core.agent.coder_federation import CoderModelFederationRouter
    router = CoderModelFederationRouter(providers={})
    router.execute_task = AsyncMock(side_effect=AssertionError(
        "le chemin live ne doit pas appeler le LLM"))
    master = EzzioMaster(federation_router=router)
    res = await master.execute_intent(
        "Quelle est la dernière version de Python 3.12 ?", channel="web")
    assert res["ok"] is True
    assert res["provider"] == "research-fabric"
    assert "truth_gate" in res and "research" in res


# --- Fan-out adaptatif (0 réseau) ---

from core.research_router import run_adaptive_research

NOW_SYNTH = 1_757_000_000.0


class FakeLLM:
    def __init__(self, text):
        self._text = text

    async def generate(self, prompt, system_prompt=None, model=None,
                       temperature=0.1, max_tokens=600):
        class R:
            pass
        r = R()
        r.content = self._text
        return r


@pytest.mark.asyncio
async def test_grounded_synthesis_filters_unsupported():
    """LLM fake : phrase supportée KEEP, ajout non prouvé REMOVE."""
    from core.research_router import grounded_synthesis
    entries = [{"claim_id": "c0",
                "text": "Le budget atteint 10 millions d'euros en France.",
                "origin": "a.example", "published_at": None, "state": "KEEP"}]
    llm = FakeLLM("[c0] En France, le budget atteint 10 millions d'euros. "
                  "[c0] Il double chaque année.")
    out = await grounded_synthesis("Budget ?", entries, llm=llm, now=NOW_SYNTH)
    # Ajout qualitatif sans ancrage : QUALIFY (marqué), pas KEEP silencieux.
    assert out["overall"] == "KEPT"
    assert "[à confirmer précisément]" in out["verified_text"]
    assert "10 millions" in out["verified_text"]


@pytest.mark.asyncio
async def test_grounded_synthesis_blocks_contradiction():
    from core.research_router import grounded_synthesis
    entries = [{"claim_id": "c0", "text": "Le budget vaut 10 millions.",
                "origin": "a.example", "published_at": None, "state": "KEEP"}]
    llm = FakeLLM("[c0] Le budget vaut 50 millions.")
    out = await grounded_synthesis("Budget ?", entries, llm=llm, now=NOW_SYNTH)
    assert out["overall"] == "BLOCKED"
    assert out["verified_text"] == ""


class CountingProvider(FakeProvider):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.calls = 0

    async def search(self, query, max_results=5, **kw):
        self.calls += 1
        self.seen_kwargs = kw
        return await super().search(query, max_results)


@pytest.mark.asyncio
async def test_adaptive_stops_after_first_when_sufficient():
    """QUICK + 1 origine avec claims → STOP, 2e source jamais appelée."""
    p1 = CountingProvider("s1", [_item("https://a.example/1", "TA", "CA")])
    p2 = CountingProvider("s2", [_item("https://b.example/2", "TB", "CB")])
    r = await run_adaptive_research("résumé vite", providers=[p1, p2])
    assert r["stop_reason"] == "SUFFICIENT"
    assert (p1.calls, p2.calls) == (1, 0)
    assert r["provider_calls"] == 1


@pytest.mark.asyncio
async def test_adaptive_escalates_on_empty_first():
    """1re source vide → 2e source (NORMAL explicite) → COMPLETE."""
    p1 = CountingProvider("s1", [])
    p2 = CountingProvider("s2", [_item("https://b.example/2", "TB", "CB")])
    r = await run_adaptive_research("compare en détail normal",
                                    providers=[p1, p2])
    assert r["breadth"] == "NORMAL"
    assert (p1.calls, p2.calls) == (1, 1)
    assert r["status"] in ("COMPLETE", "PARTIAL")


@pytest.mark.asyncio
async def test_adaptive_no_marginal_gain_stops():
    """2e source sans nouvelle origine → STOP VoI, 3e jamais appelée."""
    p1 = CountingProvider("s1", [_item("https://a.example/1", "TA", "CA")])
    p2 = CountingProvider("s2", [_item("https://a.example/autre", "TA2", "CA2")])
    p3 = CountingProvider("s3", [_item("https://c.example/3", "TC", "CC")])
    r = await run_adaptive_research("étude approfondie détaillée",
                                    providers=[p1, p2, p3])
    assert r["stop_reason"] == "NO_MARGINAL_GAIN"
    assert p3.calls == 0


@pytest.mark.asyncio
async def test_adaptive_high_risk_uses_all():
    """Question médicale → toutes les origines disponibles."""
    p1 = CountingProvider("s1", [_item("https://a.example/1", "TA", "CA")])
    p2 = CountingProvider("s2", [_item("https://b.example/2", "TB", "CB")])
    r = await run_adaptive_research("risque médical du traitement X",
                                    providers=[p1, p2])
    assert r["high_risk"] is True
    assert (p1.calls, p2.calls) == (1, 1)


@pytest.mark.asyncio
async def test_adaptive_depth_forwarded():
    """DEEP → search_depth=advanced transmis (politique Tavily §37)."""
    p1 = CountingProvider("s1", [_item("https://a.example/1", "TA", "CA")])
    await run_adaptive_research("étude approfondie détaillée complète",
                                providers=[p1])
    assert p1.seen_kwargs.get("search_depth") == "advanced"


@pytest.mark.asyncio
async def test_adaptive_all_down():
    """Tout échoue → FAILED, 0 claim, réponse absente."""
    r = await run_adaptive_research("q",
                                    providers=[FakeProvider("x", error="down")])
    assert r["status"] == "FAILED" and r["claims"] == []
    assert r["stop_reason"] == "ALL_SOURCES_USED"


@pytest.mark.asyncio
async def test_semantic_contradiction_end_to_end():
    """10 vs 12 millions, mêmes origines temporelles → CONFLICTED visible."""
    p1 = FakeProvider("s1", [_item("https://a.example/budget",
                                   "Budget 2024",
                                   "Le budget atteint 10 millions d'euros.",
                                   date="2024-03-01T00:00:00")])
    p2 = FakeProvider("s2", [_item("https://b.example/budget",
                                   "Budget 2024",
                                   "Le budget atteint 12 millions d'euros.",
                                   date="2024-03-02T00:00:00")])
    r = await run_live_research("budget 2024", providers=[p1, p2])
    assert "Contradictions numériques" in r["answer"]
    # CONFLICTED → conflit visible (QUALIFY), jamais tranché ni effacé.
    assert r["gate_verdict"] == "PASS_WITH_QUALIFIERS"
    assert r["answer"].count("[QUALIFY]") == 2
    assert "Groupes de preuve" in r["answer"]
    # Wave 3 : chaque ligne factuelle trace vers un claim (post-vérifié).
    assert r["grounding"] == "GROUNDED"
