from typing import Any

from core.providers.gemini_provider import GeminiProvider
from core.providers.iresearch_provider import IResearchProvider
from core.providers.jina_provider import JinaProvider
from core.providers.searxng_provider import SearXNGProvider
from core.providers.tavily_provider import TavilyProvider


class ResearchRouter:
    def __init__(self, providers: list[IResearchProvider]):
        self.providers = providers

    async def search(self, query: str, mode: str = "FAST", **kwargs: Any) -> dict[str, Any]:
        if not self.providers:
            raise RuntimeError("Aucun fournisseur de recherche configuré.")

        # Sélection de providers selon le mode
        if mode == "FAST":
            # Jina + Tavily en priorité
            selected = [p for p in self.providers if isinstance(p, (JinaProvider, TavilyProvider))]
        elif mode == "RESEARCH":
            # Jina + Tavily + Gemini
            selected = [p for p in self.providers if isinstance(p, (JinaProvider, TavilyProvider, GeminiProvider))]
        elif mode == "FORENSIC":
            # SearXNG (local) en priorité
            selected = [p for p in self.providers if isinstance(p, SearXNGProvider)]
        else:
            selected = self.providers

        if not selected:
            selected = self.providers

        last_error = None
        for provider in selected:
            try:
                result = await provider.search(query, **kwargs)
                if result:
                    return result
            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(f"Échec de recherche sur tous les fournisseurs. Dernier log: {last_error}")

    async def search_all(self, query: str, providers, per_source: int = 5,
                         timeout_s: float = 15.0,
                         max_concurrency: int = 3,
                         **provider_kwargs) -> dict[str, Any]:
        """Fan-out borné et parallèle : chaque source garde son statut
        (SUCCESS/PARTIAL/FAILED/TIMEOUT). Un échec n'annule pas les autres.
        La méthode search() historique est inchangée."""
        import asyncio as _aio
        import time as _time

        sem = _aio.Semaphore(max(1, max_concurrency))

        async def _one(provider) -> dict[str, Any]:
            name = getattr(provider, "name", type(provider).__name__)
            t0 = _time.perf_counter()
            try:
                async with sem:
                    try:
                        raw = await _aio.wait_for(
                            provider.search(query, max_results=per_source,
                                            **provider_kwargs),
                            timeout=timeout_s)
                    except TimeoutError:
                        return {"source": name, "status": "TIMEOUT",
                                "latency_ms": int((_time.perf_counter() - t0) * 1000),
                                "items": []}
                items = (raw.get("data", {}).get("results", [])
                         if isinstance(raw, dict) else [])
                return {"source": name, "status": "SUCCESS" if items else "PARTIAL",
                        "latency_ms": int((_time.perf_counter() - t0) * 1000),
                        "items": items if isinstance(items, list) else []}
            except Exception as exc:
                return {"source": name, "status": "FAILED",
                        "latency_ms": int((_time.perf_counter() - t0) * 1000),
                        "error": str(exc)[:200], "items": []}

        outs = await _aio.gather(*(_one(p) for p in providers))
        ok = [o for o in outs if o["status"] in ("SUCCESS", "PARTIAL") and o["items"]]
        if not outs:
            status = "FAILED"
        elif ok and len(ok) == len(outs):
            status = "COMPLETE"
        elif ok:
            status = "PARTIAL"
        else:
            status = "FAILED"
        return {"status": status, "sources": outs}


# Budgets par profondeur : requêtes, timeout, pas de fan-out illimité.
_BREADTH_BUDGET = {
    "QUICK": {"per_source": 3, "timeout_s": 12.0},
    "NORMAL": {"per_source": 5, "timeout_s": 18.0},
    "DEEP": {"per_source": 8, "timeout_s": 25.0},
    "MAX": {"per_source": 10, "timeout_s": 30.0},
}


async def run_live_research(query: str, providers=None,
                            memory_hits=None) -> dict[str, Any]:
    """Chaîne live complète : plan → fan-out → normalize → dedup →
    claims → truth gate → assemblage déterministe. Aucune synthèse LLM :
    la réponse ne contient que ce que les sources déclarent + statuts
    explicites. Internal-first : hits mémoire inclus comme MEMORY_DERIVED."""
    import time as _time

    from core.capabilities.research_fabric import (
        Breadth,
        classify_search,
    )

    t0 = _time.perf_counter()
    intent, breadth, reasons = classify_search(query or "")
    if any("aucun marqueur" in r for r in reasons):
        breadth = Breadth.QUICK  # coût par défaut : QUICK sauf demande explicite
    budget = _BREADTH_BUDGET[breadth.value]
    # Politique Tavily §37 : basic par défaut, advanced si profondeur exigée.
    depth_kwargs = ({"search_depth": "advanced"}
                    if breadth.value in ("DEEP", "MAX") else {})

    if providers is None:
        from core.capabilities.web_provider import WebProvider
        from core.providers.tavily_provider import TavilyProvider

        providers = [TavilyProvider(), _DDGAdapter(WebProvider())]

    router = ResearchRouter(providers=[])
    fanout = await router.search_all(query or "",
                                     [p for p in providers
                                      if getattr(p, "available", True)],
                                     per_source=budget["per_source"],
                                     timeout_s=budget["timeout_s"],
                                     **depth_kwargs)
    collected = [(s["source"], s["items"]) for s in fanout["sources"]]
    return _finish(query or "", intent, breadth, collected,
                   fanout["sources"], memory_hits, t0)


def _finish(query: str, intent, breadth, collected, fanout_sources,
            memory_hits, t0) -> dict[str, Any]:
    """Normalisation → dedup → claims → gate → assemblage déterministe.
    Partagé par les modes parallèle et adaptatif (une seule autorité)."""
    import time as _time

    from core.capabilities.research_fabric import (
        confidence_of,
        deduplicate,
        normalize_results,
        origin_domain,
        quality_gate,
    )
    from core.capabilities.truth_engine import (
        response_gate,
        source_results_to_claims,
        verify_grounding,
    )

    now = _time.time()
    results = []
    for src_name, items in collected:
        results.extend(normalize_results(src_name, items, query=query, now=now))
    if memory_hits:
        results.extend(memory_hits)
    unique, stats = deduplicate(results)
    claims = source_results_to_claims(unique, query or "", now)

    # Couche sémantique (Wave 2) : nœuds → graphe léger → positions
    # numériques opposées → detect_conflict existant (autorité unique).
    # Les claims en conflit avéré sont marqués AVANT le gate.
    from dataclasses import replace as _replace

    from core.capabilities.research_fabric import detect_conflict
    from core.capabilities.semantic_evidence import (
        EvidenceNode,
        SemRelation,
        build_graph,
        contradiction_stances,
        evidence_groups,
        extract_measurements,
    )
    claim_ids = [f"c{i}" for i in range(len(claims))]
    nodes = [EvidenceNode(
        claim_id=cid, text=c.text,
        origin=origin_domain(c.sources[0].locator) if c.sources else "",
        published_at=c.sources[0].published_at if c.sources else None,
        measurements=extract_measurements(c.text))
        for (c, _), cid in zip(claims, claim_ids, strict=False)]
    _, sem_edges = build_graph(nodes) if len(nodes) >= 2 else (nodes, [])
    sem_conflicts = detect_conflict(contradiction_stances(
        sem_edges, {n.claim_id: n.origin for n in nodes}))
    conflicted_ids = set()
    for key in sem_conflicts:
        try:
            _, pair = key.split(":", 1)
            left, right = pair.split("<>")
            conflicted_ids.update((left, right))
        except ValueError:
            continue
    if conflicted_ids:
        claims = [(_replace(c, conflicted=True) if cid in conflicted_ids else c, r)
                  for (c, r), cid in zip(claims, claim_ids, strict=False)]
    sem_groups = evidence_groups(nodes, sem_edges) if sem_edges else []
    sem_checked = len(nodes) >= 2

    if not claims:
        verdict, decisions = "BLOCKED", []
    else:
        verdict, decisions = response_gate([(c, r) for c, r in claims])

    # Auto-contrôle phrase-à-preuve (Wave 3.5) : chaque texte de claim
    # est revérifié contre l'ensemble de preuves (conflits inclus).
    from core.capabilities.truth_engine import build_evidence_context
    from core.capabilities.truth_engine import verify_sentence as _vsent
    _entries = [{"claim_id": cid, "text": c.text,
                 "origin": origin_domain(c.sources[0].locator) if c.sources else "",
                 "published_at": c.sources[0].published_at if c.sources else None,
                 "state": act}
                for (c, _), (_, act, _), cid
                in zip(claims, decisions, claim_ids, strict=False)]
    _ev_ctx = build_evidence_context(_entries)
    claim_states = {cid: act for (_, act, _), cid in zip(decisions, claim_ids, strict=False)}
    sentence_check = {e["claim_id"]: _vsent(e["text"], _ev_ctx, now)[0]
                      for e in _entries}

    by_state: dict[str, list] = {}
    for (claim, _), (_, action, reason) in zip(claims, decisions, strict=False):
        by_state.setdefault(action.value, []).append((claim, reason))
    kept = by_state.get("KEEP", [])
    origins = sorted({origin_domain(c.sources[0].locator)
                      for c, _ in kept if c.sources}
                     or {origin_domain(r.locator) for r in unique})
    n_origins = len([o for o in origins if o])
    conf = confidence_of(n_origins, bool(kept), False,
                         any((c.sources[0].published_at or 0) > now - 7 * 86400
                             for c, _ in kept if c.sources) if kept else False)
    gate, missing = quality_gate(n_origins, False, conf in ("HIGH", "MEDIUM"),
                                 sem_checked, True, True)

    lines = [f"Recherche live : {stats['pages']} résultats, "
             f"{stats['distinct']} documents distincts, "
             f"{stats['independent_origins']} origines indépendantes. "
             f"Confiance : {conf.value}. Grille qualité : {gate}."]
    cid_of = {id(c): cid for (c, _), cid in zip(claims, claim_ids, strict=False)}
    if kept:
        lines.append("Faits corroborés :")
        for c, _ in kept[:6]:
            loc = c.sources[0].locator if c.sources else "?"
            lines.append(f"- [{cid_of.get(id(c), '?')}] {c.text[:280]} "
                         f"[source : {loc}]")
    for action in ("QUALIFY", "REMOVE", "MARK_UNKNOWN"):
        for c, reason in by_state.get(action, [])[:4]:
            lines.append(f"- [{cid_of.get(id(c), '?')}] [{action}] "
                         f"{c.text[:200]} ({reason})")
    if missing:
        lines.append("Limites explicites : " + "; ".join(missing) + ".")
    if sem_groups:
        lines.append(f"Groupes de preuve : {len(sem_groups)} "
                     f"(copies/miroirs fusionnés, jamais multi-comptés).")
    n_contra = sum(1 for e in sem_edges
                   if e.relation == SemRelation.CONTRADICTS)
    if n_contra:
        lines.append(f"Contradictions numériques : {n_contra} opposition(s) "
                     f"même unité/même fenêtre → marquées CONFLICTED.")
    lines.append("Note : analyse limitée aux mesures et au recouvrement "
                 "lexical (pas de NLP) ; les oppositions littérales seules "
                 "sont prises en compte.")

    total_ms = int((_time.perf_counter() - t0) * 1000)
    answer = "\n".join(lines)
    grounding, orphans = verify_grounding(answer, claim_ids)
    if grounding != "GROUNDED":  # fail-visible, jamais silencieux
        answer += "\nNote : " + str(len(orphans)) + " ligne(s) sans traçabilité claim."
    ok_sources = [s for s in fanout_sources
                  if s["status"] in ("SUCCESS", "PARTIAL") and s.get("items")]
    if not fanout_sources:
        status = "FAILED"
    elif ok_sources and len(ok_sources) == len(fanout_sources):
        status = "COMPLETE"
    elif ok_sources:
        status = "PARTIAL"
    else:
        status = "FAILED"
    return {"status": status,
            "intent": intent.value, "breadth": breadth.value,
            "stats": stats, "independent_origins": n_origins,
            "confidence": conf.value, "quality": gate,
            "claims": claims, "gate_verdict": verdict,
            "claim_ids": claim_ids, "claim_states": claim_states,
            "sentence_check": sentence_check, "grounding": grounding,
            "evidence_entries": _entries,
            "answer": answer,
            "sources": [{"source": s["source"], "status": s["status"],
                         "latency_ms": s["latency_ms"]} for s in fanout_sources],
            "latency_ms": total_ms}


class _DDGAdapter:
    """Adapte WebProvider (shape {ok,data}) au contrat IResearchProvider."""

    name = "ddg"

    def __init__(self, web_provider) -> None:
        self._web = web_provider

    async def search(self, query: str, max_results: int = 5,
                     **_ignored) -> dict[str, Any]:
        raw = await self._web.search(query, limit=max_results)
        if not isinstance(raw, dict) or not raw.get("ok"):
            raise RuntimeError(str(raw.get("error", "web.search refusé"))
                               if isinstance(raw, dict) else "web.search refusé")
        return {"provider": self.name,
                "data": {"results": raw.get("data", []),
                         "total": raw.get("count", 0)}}


# Cibles de diversité par profondeur : arrêt dès que suffisant (VoI).
_ADAPTIVE_TARGETS = {"QUICK": 1, "NORMAL": 2, "DEEP": 3, "MAX": 3}

# Haut risque → escalade maximale sur les origines disponibles (§35).
# Exposé (alias public) : source unique pour la décision de routage.
_HIGH_RISK_KEYWORDS = (
    "juridique", "légal", "legal", "médical", "medical", "santé",
    "financier", "financial", "investissement", "politique", "election",
    "élection", "sécurité", "security", "vulnérabilité", "safety",
)
HIGH_RISK_KEYWORDS = _HIGH_RISK_KEYWORDS


async def run_adaptive_research(query: str, providers=None,
                                memory_hits=None, synthesize: bool = False,
                                synthesizer=None) -> dict[str, Any]:
    """Fan-out adaptatif : UNE source → SUFFISANT ? → STOP, sinon source
    suivante. Gain marginal nul → STOP (VoI). Haut risque → toutes les
    origines disponibles. Même _finish que le mode parallèle (0 second
    chemin de vérité). Slots Brave/SearXNG : tout IResearchProvider passé
    en `providers` participe à l'ordre ; absents → DEFERRED documenté.
    synthesize=True ajoute une synthèse LLM ancrée post-vérifiée
    (défaut False : assemblage déterministe, frugalité)."""
    import time as _time

    from core.capabilities.research_fabric import (
        Breadth,
        classify_search,
        deduplicate,
        normalize_results,
    )

    t0 = _time.perf_counter()
    q = query or ""
    intent, breadth, reasons = classify_search(q)
    if any("aucun marqueur" in r for r in reasons):
        breadth = Breadth.QUICK
    budget = _BREADTH_BUDGET[breadth.value]
    depth_kwargs = ({"search_depth": "advanced"}
                    if breadth.value in ("DEEP", "MAX") else {})
    high_risk = any(k in q.lower() for k in _HIGH_RISK_KEYWORDS)

    if providers is None:
        from core.capabilities.web_provider import WebProvider
        from core.providers.tavily_provider import TavilyProvider

        providers = [TavilyProvider(), _DDGAdapter(WebProvider())]
    ordered = [p for p in providers if getattr(p, "available", True)]
    if high_risk:
        target = len(ordered) or 1
    else:
        target = min(_ADAPTIVE_TARGETS[breadth.value], len(ordered) or 1)

    router = ResearchRouter(providers=[])
    collected, fanout_sources, rounds = [], [], []
    now = _time.time()
    seen_origins: set = set()
    stop_reason = "BUDGET"
    for i, provider in enumerate(ordered):
        fanout = await router.search_all(
            q, [provider], per_source=budget["per_source"],
            timeout_s=budget["timeout_s"], **depth_kwargs)
        src = fanout["sources"][0] if fanout["sources"] else {
            "source": getattr(provider, "name", "?"), "status": "FAILED",
            "latency_ms": 0, "items": []}
        fanout_sources.append(src)
        collected.append((src["source"], src.get("items", [])))
        probe = deduplicate(normalize_results(
            src["source"], src.get("items", []), query=q, now=now))[1]
        # Origines cumulées (approximation par round : union via _finish
        # final ; ici comptage round + mémoire des rounds précédents).
        from core.capabilities.research_fabric import origin_domain
        for _name, _items in collected:
            for _it in normalize_results(_name, _items, query=q, now=now):
                seen_origins.add(origin_domain(_it.locator))
        n_origins = len([o for o in seen_origins if o])
        n_claims = probe["distinct"]
        rounds.append({"source": src["source"], "status": src["status"],
                       "n_origins": n_origins, "n_claims": n_claims})
        if n_claims >= 1 and n_origins >= target:
            stop_reason = "SUFFICIENT"
            break
        if i > 0 and n_origins == rounds[i - 1]["n_origins"] and n_claims >= 1:
            stop_reason = "NO_MARGINAL_GAIN"  # VoI : 2e source sans gain
            break

    if stop_reason == "BUDGET":
        stop_reason = "ALL_SOURCES_USED"

    out = _finish(q, intent, breadth, collected, fanout_sources,
                  memory_hits, t0)
    out["mode"] = "ADAPTIVE"
    out["rounds"] = rounds
    out["stop_reason"] = stop_reason
    out["provider_calls"] = len(fanout_sources)
    out["high_risk"] = high_risk
    if synthesize and out.get("claims"):
        try:
            out["synthesis"] = await grounded_synthesis(
                q, out.get("evidence_entries", []),
                llm=synthesizer, now=_time.time())
        except Exception as exc:
            out["synthesis"] = {"overall": "FAILED", "error": str(exc)[:200],
                                "verified_text": "", "draft": ""}
    return out


_SYNTH_SYSTEM = (
    "Tu es un synthétiseur factuel strict. Règles absolues : "
    "reformule uniquement les preuves fournies ; chaque phrase factuelle "
    "DOIT citer ses [cid] ; n'ajoute aucun chiffre, date, nom, lieu, "
    "causalité ou URL absent des preuves ; expose les conflits au lieu de "
    "trancher ; conserve les incertitudes ; ne transforme jamais une "
    "inférence en fait. Réponse concise en français.")


async def grounded_synthesis(question: str, entries, llm=None,
                             model: str = "hermes3:8b",
                             max_tokens: int = 600,
                             now: float = 0.0) -> dict[str, Any]:
    """Synthèse LLM ancrée : contexte = preuves avec états explicites ;
    sortie = post-vérifiée phrase à phrase (verify_response). Le LLM est
    SYNTHESIZER, jamais autorité : tout ajout est REMOVE/BLOCK.
    llm injectable (fakes en tests) ; défaut = OllamaProvider local (0 quota)."""
    import time as _time

    from core.capabilities.truth_engine import (
        build_evidence_context,
        verify_response,
    )

    t0 = _time.perf_counter()
    ctx = build_evidence_context(entries or [])
    ev_lines = []
    for e in entries or []:
        cid = e.get("claim_id", "?")
        ev_lines.append(f"[{cid}] ({e.get('state', 'UNKNOWN')}) "
                        f"origine={e.get('origin', '?')} :: {e.get('text', '')[:400]}")
    prompt = (f"Question : {(question or '')[:300]}\nPreuves :\n"
              + "\n".join(ev_lines[:12])
              + "\nSynthèse avec citations [cid] :")
    if llm is None:
        from core.providers.ollama_provider import OllamaProvider
        llm = OllamaProvider()
    resp = await llm.generate(prompt, system_prompt=_SYNTH_SYSTEM,
                              model=model, temperature=0.1,
                              max_tokens=max_tokens)
    draft = (resp.content if resp is not None else "") or ""
    check = verify_response(draft, ctx, now or _time.time())
    return {"draft": draft, "verified_text": check["text"],
            "overall": check["overall"], "reports": check["reports"],
            "stats": check["stats"], "model": model,
            "latency_ms": int((_time.perf_counter() - t0) * 1000)}
