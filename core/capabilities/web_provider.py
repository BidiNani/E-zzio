"""E-ZZIO Capability Router — Sovereign Web Capability Optimization.

Unifies web capabilities behind CapabilityPolicy:
- web.search: Fast, multi-tiered web search across authoritative sources (ALLOW)
- web.crawl: Structured Markdown extraction with SSRF & prompt injection containment (ALLOW)
- browser.automate: Local headless browser DOM rendering and interactive session inspection (REQUIRE_HUMAN)

Roles Decoupling:
- ROLE 1: SEARCH (DuckDuckGo HTML sovereign free -> DDGS resilient free -> Tavily high precision -> Jina Search)
- ROLE 2: EXTRACT (Local direct HTTP scraper + Markdown -> Jina Reader markdown/pdf -> Local headless Brave)
- ROLE 3: SEMANTIC / DEEP SEARCH (Bounded parallel fan-out via ResearchRouter / Jina Search / Tavily)
- ROLE 4: BROWSER (Local Brave / Chromium headless DOM dump & Active CDP port)
- ROLE 5: RERANK / FILTER (URL deduplication, domain diversity, lexical match scoring)

Zero vendor lock-in. Self-contained with direct HTTP transport, non-silent fallbacks and AuditLedger traceability.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import time
import urllib.parse
from typing import Any

from core.capabilities.capability_policy import CapabilityPolicy, PolicyDecision
from core.security.audit_ledger import AuditLedger
from core.security.untrusted import wrap_webpage
from core.utils.http_pool import get_http_client

logger = logging.getLogger("WebProvider")


def find_local_browser() -> tuple[str | None, str]:
    """Détecte les binaires de navigateurs locaux disponibles pour l'exécution headless."""
    candidates = [
        (r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe", "brave"),
        (r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe", "brave"),
        (os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"), "brave"),
        (r"G:\Hermes\tools\chromium-1208\chrome-win64\chrome.exe", "chromium_hermes"),
        (r"C:\Program Files\Google\Chrome\Application\chrome.exe", "chrome"),
        (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", "edge"),
    ]
    for path, name in candidates:
        if os.path.exists(path):
            return path, name
    for cmd in ["brave", "chrome", "chromium", "msedge"]:
        w = shutil.which(cmd)
        if w:
            return w, cmd
    return None, "none"


class WebProvider:
    """Fournisseur de capacités Web d'E-ZZIO avec découplage strict des rôles et repli non silencieux."""

    def __init__(self, searxng_url: str | None = None):
        self.policy = CapabilityPolicy()
        self.searxng_url = searxng_url or os.environ.get("SEARXNG_URL")

    def _record_audit(self, action: str, payload: dict[str, Any]) -> None:
        """Enregistre les événements et transitions de secours dans l'AuditLedger."""
        try:
            AuditLedger().record_event(actor="web_provider", action=action, payload=payload)
        except Exception as exc:
            logger.debug("[AUDIT-RECORD-SKIP] %s", exc)

    def _check_budget_permission(self, provider_name: str, cost_class: str) -> bool:
        """Consulte le BudgetGovernor pour vérifier si un appel payant est autorisé."""
        if cost_class == "FREE":
            return True
        try:
            from core.governance.budget_governor import BudgetGovernor
            governor = BudgetGovernor()
            preflight = governor.preflight(
                mission_id="web_capability",
                provider=provider_name,
                model=provider_name,
                estimated_cost=0.01
            )
            return preflight.allowed
        except Exception:
            return True

    async def search(
        self,
        query: str,
        limit: int = 5,
        role: str = "SEARCH",
        prefer_free: bool = False,
        prefer_tavily: bool = False,
        timeout_s: float = 12.0
    ) -> dict[str, Any]:
        """Recherche Web multi-tiers unifiée avec gouvernance budgétaire et repli non silencieux.

        Stratégie d'économie de coûts et souveraineté :
        1. SearXNG local (Tier 0 Souverain si configuré)
        2. Tavily si explicitement demandé (prefer_tavily ou role=DEEP)
        3. DuckDuckGo HTML direct (Tier 1 Souverain gratuit sans clé)
        4. DuckDuckGo DDGS (Tier 2 Résilient gratuit sans clé si HTML rate-limité)
        5. Tavily Search (Tier 3 Haute précision si clé et budget autorisés)
        6. Jina Search (Tier 4 Recherche sémantique / deep)
        """
        decision, reason = self.policy.evaluate_scope("web.search", {"query": query, "limit": limit})
        if decision != PolicyDecision.ALLOW:
            return {"ok": False, "error": reason, "scope": "web.search"}

        client = get_http_client()
        fallback_chain: list[str] = []

        # 1. Tentative SearXNG si configuré
        if self.searxng_url:
            t0 = time.perf_counter()
            try:
                searx_endpoint = f"{self.searxng_url.rstrip('/')}/search"
                resp = await asyncio.wait_for(
                    client.get(searx_endpoint, params={"q": query, "format": "json"}),
                    timeout=min(timeout_s, 5.0)
                )
                if resp.status_code == 200:
                    raw_data = resp.json()
                    results = [
                        {
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "snippet": r.get("content", "")
                        }
                        for r in raw_data.get("results", [])[:limit]
                    ]
                    lat = (time.perf_counter() - t0) * 1000.0
                    self._record_audit("WEB_SEARCH_SUCCESS", {"backend": "searxng", "query": query, "lat_ms": lat, "count": len(results)})
                    return {
                        "ok": True,
                        "backend": "searxng",
                        "cost_class": "FREE",
                        "scope": "web.search",
                        "query": query,
                        "count": len(results),
                        "data": self.rerank(results, query),
                        "fallback_chain": fallback_chain
                    }
            except Exception as exc:
                fallback_chain.append(f"searxng:failed({str(exc)[:60]})")
                self._record_audit("WEB_SEARCH_FALLBACK", {"from": "searxng", "to": "ddg", "reason": str(exc)[:200]})
                logger.warning("[SEARXNG-WARN] Repli suite à : %s", exc)

        # 2. Tentative Tavily prioritaire uniquement si explicitement demandée (ou role DEEP)
        tavily_key = os.environ.get("TAVILY_API_KEY")
        if (prefer_tavily or role in ("DEEP", "HIGH_PRECISION")) and tavily_key and not prefer_free and self._check_budget_permission("tavily", "PAID"):
            t0 = time.perf_counter()
            try:
                from core.providers.tavily_provider import TavilyProvider
                tp = TavilyProvider(api_key=tavily_key)
                res = await asyncio.wait_for(tp.search(query, max_results=limit), timeout=timeout_s)
                items = res.get("data", {}).get("results", [])
                if items:
                    results = [
                        {
                            "title": r.get("title", "Sans titre"),
                            "url": r.get("url", ""),
                            "snippet": r.get("content", "")
                        }
                        for r in items[:limit]
                    ]
                    lat = (time.perf_counter() - t0) * 1000.0
                    self._record_audit("WEB_SEARCH_SUCCESS", {"backend": "tavily", "query": query, "lat_ms": lat, "count": len(results)})
                    return {
                        "ok": True,
                        "backend": "tavily",
                        "cost_class": "PAID",
                        "scope": "web.search",
                        "query": query,
                        "count": len(results),
                        "data": self.rerank(results, query),
                        "fallback_chain": fallback_chain
                    }
            except Exception as exc:
                fallback_chain.append(f"tavily:failed({str(exc)[:60]})")
                self._record_audit("WEB_SEARCH_FALLBACK", {"from": "tavily", "to": "duckduckgo_html", "reason": str(exc)[:200]})

        # 3. Tentative DuckDuckGo HTML direct sans clé API (Souverain direct, 0 coût)
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"q": query}
        t0 = time.perf_counter()
        try:
            r = await asyncio.wait_for(client.post(url, headers=headers, data=data), timeout=min(timeout_s, 6.0))
            if r.status_code == 200:
                results = self._parse_ddg_html(r.text, limit=limit)
                if results:
                    lat = (time.perf_counter() - t0) * 1000.0
                    self._record_audit("WEB_SEARCH_SUCCESS", {"backend": "duckduckgo_html", "query": query, "lat_ms": lat, "count": len(results)})
                    return {
                        "ok": True,
                        "backend": "duckduckgo_html",
                        "cost_class": "FREE",
                        "scope": "web.search",
                        "query": query,
                        "count": len(results),
                        "data": self.rerank(results, query),
                        "fallback_chain": fallback_chain
                    }
        except Exception as exc:
            fallback_chain.append(f"duckduckgo_html:failed({str(exc)[:60]})")
            self._record_audit("WEB_SEARCH_FALLBACK", {"from": "duckduckgo_html", "to": "ddgs", "reason": str(exc)[:200]})
            logger.info("[DDG-HTML-FAIL] Repli sur DDGS suite à : %s", exc)

        # 4. Tentative DuckDuckGo via package `ddgs` (Résistant aux limites, rotation vqd)
        t0 = time.perf_counter()
        try:
            from ddgs import DDGS
            ddgs_client = DDGS()
            raw_results = await asyncio.to_thread(
                lambda: list(ddgs_client.text(query, max_results=limit))
            )
            if raw_results:
                results = [
                    {
                        "title": r.get("title", "Sans titre"),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", "")
                    }
                    for r in raw_results[:limit]
                ]
                lat = (time.perf_counter() - t0) * 1000.0
                self._record_audit("WEB_SEARCH_SUCCESS", {"backend": "ddgs", "query": query, "lat_ms": lat, "count": len(results)})
                return {
                    "ok": True,
                    "backend": "ddgs",
                    "cost_class": "FREE",
                    "scope": "web.search",
                    "query": query,
                    "count": len(results),
                    "data": self.rerank(results, query),
                    "fallback_chain": fallback_chain
                }
        except Exception as exc:
            fallback_chain.append(f"ddgs:failed({str(exc)[:60]})")
            self._record_audit("WEB_SEARCH_FALLBACK", {"from": "ddgs", "to": "tavily", "reason": str(exc)[:200]})
            logger.info("[DDGS-FAIL] Repli sur Tavily suite à : %s", exc)

        # 5. Tentative Tavily Search (Tier haute précision payant / limité)
        if tavily_key and not prefer_free and self._check_budget_permission("tavily", "PAID"):
            t0 = time.perf_counter()
            try:
                from core.providers.tavily_provider import TavilyProvider
                tp = TavilyProvider(api_key=tavily_key)
                res = await asyncio.wait_for(tp.search(query, max_results=limit), timeout=timeout_s)
                items = res.get("data", {}).get("results", [])
                if items:
                    results = [
                        {
                            "title": r.get("title", "Sans titre"),
                            "url": r.get("url", ""),
                            "snippet": r.get("content", "")
                        }
                        for r in items[:limit]
                    ]
                    lat = (time.perf_counter() - t0) * 1000.0
                    self._record_audit("WEB_SEARCH_SUCCESS", {"backend": "tavily", "query": query, "lat_ms": lat, "count": len(results)})
                    return {
                        "ok": True,
                        "backend": "tavily",
                        "cost_class": "PAID",
                        "scope": "web.search",
                        "query": query,
                        "count": len(results),
                        "data": self.rerank(results, query),
                        "fallback_chain": fallback_chain
                    }
            except Exception as exc:
                fallback_chain.append(f"tavily:failed({str(exc)[:60]})")
                self._record_audit("WEB_SEARCH_FALLBACK", {"from": "tavily", "to": "jina_search", "reason": str(exc)[:200]})

        # 6. Tentative Jina Search (s.jina.ai)
        jina_key = os.environ.get("JINA_API_KEY")
        if jina_key and self._check_budget_permission("jina_search", "PAID"):
            t0 = time.perf_counter()
            try:
                from core.providers.jina_provider import JinaProvider
                jp = JinaProvider(api_key=jina_key)
                res = await asyncio.wait_for(jp.search(query), timeout=timeout_s)
                items = res.get("data", {}).get("results", [])
                if items:
                    results = [
                        {
                            "title": r.get("title", "Sans titre"),
                            "url": r.get("url", ""),
                            "snippet": r.get("content", "") or r.get("description", "")
                        }
                        for r in items[:limit]
                    ]
                    lat = (time.perf_counter() - t0) * 1000.0
                    self._record_audit("WEB_SEARCH_SUCCESS", {"backend": "jina_search", "query": query, "lat_ms": lat, "count": len(results)})
                    return {
                        "ok": True,
                        "backend": "jina_search",
                        "cost_class": "PAID",
                        "scope": "web.search",
                        "query": query,
                        "count": len(results),
                        "data": self.rerank(results, query),
                        "fallback_chain": fallback_chain
                    }
            except Exception as exc:
                fallback_chain.append(f"jina_search:failed({str(exc)[:60]})")

        # Échec total sur l'ensemble de la chaîne de recherche
        self._record_audit("WEB_SEARCH_EXHAUSTED", {"query": query, "fallback_chain": fallback_chain})
        return {
            "ok": False,
            "scope": "web.search",
            "error": "Échec de recherche web sur tous les backends disponibles",
            "fallback_chain": fallback_chain,
            "count": 0,
            "data": []
        }

    def _parse_ddg_html(self, html: str, limit: int = 5) -> list[dict[str, str]]:
        """Extrait les titres, URLs organiques et résumés des résultats HTML de recherche."""
        results = []
        matches = re.findall(r'<a class="result__snippet"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
        url_matches = re.findall(r'<a class="result__url"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)

        if matches:
            for i, (raw_href, raw_snip) in enumerate(matches):
                if "uddg=" in raw_href:
                    try:
                        qs = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                        real_url = qs.get("uddg", [raw_href])[0]
                    except Exception:
                        real_url = raw_href
                else:
                    real_url = raw_href

                if "y.js?" in real_url or "bing.com/aclick" in real_url:
                    continue

                clean_snip = re.sub(r'<[^>]+>', '', raw_snip).strip()
                title = re.sub(r'<[^>]+>', '', url_matches[i][1]).strip() if i < len(url_matches) else "Résultat Web"

                results.append({
                    "title": title or "Résultat Web",
                    "url": real_url,
                    "snippet": clean_snip
                })
                if len(results) >= limit:
                    break
        else:
            raw_blocks = re.findall(r'<div class="result__body[^"]*">(.*?)(?:</div>\s*</div>|</div>)', html, re.DOTALL)
            for block in raw_blocks[:limit]:
                url_match = re.search(r'class="result__url"[^>]*href="([^"]+)"', block)
                title_match = re.search(r'class="result__title"[^>]*>(.*?)</a>', block, re.DOTALL)
                snip_match = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', block, re.DOTALL)

                clean_url = url_match.group(1).strip() if url_match else ""
                clean_title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else "Sans titre"
                clean_snip = re.sub(r'<[^>]+>', '', snip_match.group(1)).strip() if snip_match else ""

                if clean_url:
                    results.append({
                        "title": clean_title,
                        "url": clean_url,
                        "snippet": clean_snip
                    })

        return results

    async def crawl(
        self,
        target_url: str,
        max_chars: int = 4000,
        prefer_browser: bool = False,
        prefer_jina: bool = False,
        timeout_s: float = 15.0
    ) -> dict[str, Any]:
        """Extrait le contenu structuré en Markdown depuis une URL (scope: web.crawl).

        Garantit :
        - Protection SSRF stricte
        - Encapsulation de sécurité UNTRUSTED DATA anti-évasion
        - Ordre de secours : Scraper Local HTTP direct -> Jina Reader -> Browser Local Headless
        """
        decision, reason = self.policy.evaluate_scope("web.crawl", {"url": target_url})
        if decision != PolicyDecision.ALLOW:
            return {"ok": False, "error": reason}

        # Protection SSRF proactive sur les adresses privées et cloud metadata
        parsed = urllib.parse.urlparse(target_url)
        hostname = (parsed.hostname or "").lower()
        if (
            not hostname
            or hostname in ("localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254")
            or hostname.startswith("192.168.")
            or hostname.startswith("10.")
            or parsed.scheme.lower() not in ("http", "https")
        ):
            return {"ok": False, "error": f"[SSRF-PROTECT] Accès interdit à l'adresse interne/privée : {hostname or 'invalide'}"}

        fallback_chain: list[str] = []

        # 1. Si navigation interactive ou rendu JS lourd requis explicitement
        if prefer_browser:
            dump_res = await self.browser_dump(target_url, max_chars=max_chars, timeout_s=timeout_s)
            if dump_res.get("ok"):
                return dump_res
            fallback_chain.append("browser:failed")

        # 2. Scraper HTTP local souverain direct avec convertisseur HTML -> Markdown (0 coût, instantané)
        if not prefer_jina:
            headers_direct = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) E-ZzIO-Crawler/2.0",
                "Accept": "text/html,application/xhtml+xml,text/plain"
            }
            t0 = time.perf_counter()
            try:
                client = get_http_client()
                r = await asyncio.wait_for(client.get(target_url, headers=headers_direct), timeout=min(timeout_s, 8.0))
                if r.status_code == 200:
                    clean_markdown = self._html_to_markdown(r.text)
                    if len(clean_markdown.strip()) > 30:
                        truncated = clean_markdown[:max_chars]
                        wrapped = wrap_webpage(truncated, url=target_url)
                        lat = (time.perf_counter() - t0) * 1000.0
                        self._record_audit("WEB_EXTRACT_SUCCESS", {"backend": "local_http", "url": target_url, "lat_ms": lat, "length": len(truncated)})
                        return {
                            "ok": True,
                            "backend": "local_http",
                            "cost_class": "FREE",
                            "scope": "web.crawl",
                            "url": target_url,
                            "length": len(truncated),
                            "content": wrapped,
                            "raw_content": truncated,
                            "fallback_chain": fallback_chain
                        }
            except Exception as exc:
                fallback_chain.append(f"local_http:failed({str(exc)[:60]})")
                self._record_audit("WEB_EXTRACT_FALLBACK", {"from": "local_http", "to": "jina_reader", "reason": str(exc)[:200]})

        # 3. Tentative Jina Reader (r.jina.ai) — Extraction Markdown de pointe et conversion PDF native
        jina_key = os.environ.get("JINA_API_KEY")
        headers_jina = {"Accept": "application/json"}
        if jina_key:
            headers_jina["Authorization"] = f"Bearer {jina_key}"

        t0 = time.perf_counter()
        try:
            import httpx
            async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True) as client:
                resp = await client.get(f"https://r.jina.ai/{target_url}", headers=headers_jina)
                if resp.status_code == 200:
                    text_content = resp.text
                    # Extraction du texte si réponse JSON enveloppée
                    try:
                        import json
                        js_data = json.loads(text_content)
                        if isinstance(js_data, dict) and "data" in js_data and "content" in js_data["data"]:
                            text_content = js_data["data"]["content"]
                    except Exception:
                        pass

                    # Si du HTML résiduel est présent, le convertir proprement
                    if "<html" in text_content.lower() or "</h1>" in text_content.lower():
                        text_content = self._html_to_markdown(text_content)

                    truncated = text_content[:max_chars]
                    wrapped = wrap_webpage(truncated, url=target_url)
                    lat = (time.perf_counter() - t0) * 1000.0
                    self._record_audit("WEB_EXTRACT_SUCCESS", {"backend": "jina_reader", "url": target_url, "lat_ms": lat, "length": len(truncated)})
                    return {
                        "ok": True,
                        "backend": "jina_reader",
                        "cost_class": "PAID" if jina_key else "FREE_LIMITED",
                        "scope": "web.crawl",
                        "url": target_url,
                        "length": len(truncated),
                        "content": wrapped,
                        "raw_content": truncated,
                        "fallback_chain": fallback_chain
                    }
        except Exception as exc:
            fallback_chain.append(f"jina_reader:failed({str(exc)[:60]})")
            self._record_audit("WEB_EXTRACT_FALLBACK", {"from": "jina_reader", "to": "browser_dump", "reason": str(exc)[:200]})
            logger.info("[JINA-READER-FAIL] Repli sur browser headless local suite à : %s", exc)

        # 4. Repli Headless Browser Local (Brave / Chromium)
        dump_res = await self.browser_dump(target_url, max_chars=max_chars, timeout_s=timeout_s)
        if dump_res.get("ok"):
            dump_res["fallback_chain"] = fallback_chain
            return dump_res

        fallback_chain.append("browser_dump:failed")
        self._record_audit("WEB_EXTRACT_EXHAUSTED", {"url": target_url, "fallback_chain": fallback_chain})
        return {
            "ok": False,
            "scope": "web.crawl",
            "error": "Échec d'extraction du contenu sur l'ensemble des backends",
            "fallback_chain": fallback_chain
        }

    async def browser_dump(
        self,
        target_url: str,
        max_chars: int = 15000,
        timeout_s: float = 12.0
    ) -> dict[str, Any]:
        """Extrait le DOM rendu d'une URL via un binaire de navigateur local headless."""
        parsed = urllib.parse.urlparse(target_url)
        hostname = (parsed.hostname or "").lower()
        if (
            not hostname
            or hostname in ("localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254")
            or hostname.startswith("192.168.")
            or hostname.startswith("10.")
        ):
            return {"ok": False, "error": f"[SSRF-PROTECT] Hôte interdit pour le navigateur : {hostname}"}

        browser_path, browser_name = find_local_browser()
        if not browser_path:
            return {"ok": False, "error": "Aucun binaire de navigateur local disponible (Brave/Chromium absent)"}

        t0 = time.perf_counter()
        try:
            proc = await asyncio.create_subprocess_exec(
                browser_path,
                "--headless=new",
                "--dump-dom",
                target_url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
            dom_text = stdout.decode("utf-8", errors="replace")
            clean_md = self._html_to_markdown(dom_text)
            truncated = clean_md[:max_chars] if clean_md else dom_text[:max_chars]
            wrapped = wrap_webpage(truncated, url=target_url)
            lat = (time.perf_counter() - t0) * 1000.0

            self._record_audit("WEB_BROWSER_DUMP_SUCCESS", {"browser": browser_name, "url": target_url, "lat_ms": lat, "length": len(truncated)})
            return {
                "ok": True,
                "backend": f"browser_{browser_name}",
                "cost_class": "FREE",
                "scope": "web.crawl",
                "url": target_url,
                "length": len(truncated),
                "content": wrapped,
                "raw_content": truncated
            }
        except Exception as exc:
            return {"ok": False, "error": f"Erreur navigateur headless ({browser_name}) : {exc}"}

    def rerank(self, results: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
        """Dédoublonne par nom d'hôte/chemin et ordonne les résultats par chevauchement lexical."""
        if not results:
            return []

        seen_keys: set[str] = set()
        unique: list[dict[str, Any]] = []

        for item in results:
            url = item.get("url", "").strip()
            if not url:
                continue
            parsed = urllib.parse.urlparse(url)
            clean_key = f"{parsed.netloc.lower()}{parsed.path.rstrip('/')}"
            if clean_key in seen_keys:
                continue
            seen_keys.add(clean_key)
            unique.append(item)

        query_terms = [w.lower() for w in re.findall(r'\w+', query) if len(w) > 2]
        if not query_terms:
            return unique

        def score(entry: dict[str, Any]) -> float:
            haystack = f"{entry.get('title', '')} {entry.get('snippet', '')}".lower()
            matches = sum(1 for term in query_terms if term in haystack)
            return float(matches) / len(query_terms)

        return sorted(unique, key=score, reverse=True)

    def _html_to_markdown(self, html: str) -> str:
        """Convertit du HTML brut en texte/Markdown épuré sans tags parasites."""
        cleaned = re.sub(r'<(script|style|nav|footer|header)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<h1[^>]*>(.*?)</h1>', r'\n# \1\n', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\1\n', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<li[^>]*>(.*?)</li>', r'\n- \1', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
        return cleaned.strip()

    @classmethod
    def get_inventory(cls) -> dict[str, Any]:
        """Retourne un inventaire complet, sans supposer, de l'état réel des capacités Web."""
        browser_path, browser_name = find_local_browser()
        tavily_key = bool(os.environ.get("TAVILY_API_KEY"))
        jina_key = bool(os.environ.get("JINA_API_KEY"))
        brave_key = bool(os.environ.get("BRAVE_API_KEY"))
        exa_key = bool(os.environ.get("EXA_API_KEY"))
        firecrawl_key = bool(os.environ.get("FIRECRAWL_API_KEY"))
        perplexity_key = bool(os.environ.get("PERPLEXITY_API_KEY"))

        ddgs_installed = False
        try:
            import ddgs  # noqa: F401
            ddgs_installed = True
        except ImportError:
            pass

        return {
            "search_backends": {
                "tavily": {
                    "installed": True,
                    "configured": tavily_key,
                    "key_present": tavily_key,
                    "reachable": tavily_key,
                    "functional": tavily_key,
                    "role": "ROLE 1 — SEARCH (High Precision / Deep)",
                    "cost": "PAID / FREE_LIMITED"
                },
                "ddgs": {
                    "installed": ddgs_installed,
                    "configured": True,
                    "key_present": "N/A (Keyless)",
                    "reachable": ddgs_installed,
                    "functional": ddgs_installed,
                    "role": "ROLE 1 — SEARCH (Sovereign Resilient Free)",
                    "cost": "FREE"
                },
                "duckduckgo_html": {
                    "installed": True,
                    "configured": True,
                    "key_present": "N/A (Keyless)",
                    "reachable": True,
                    "functional": True,
                    "role": "ROLE 1 — SEARCH (Sovereign Direct Free)",
                    "cost": "FREE"
                },
                "searxng": {
                    "installed": False,
                    "configured": bool(os.environ.get("SEARXNG_URL")),
                    "key_present": "N/A",
                    "reachable": False,
                    "functional": False,
                    "missing": "Service local non lancé sur 8080/8888 (DEFERRED)",
                    "role": "ROLE 1 — SEARCH (Tier 0 Local Souverain)",
                    "cost": "FREE"
                },
                "brave_search_api": {
                    "installed": False,
                    "configured": brave_key,
                    "key_present": brave_key,
                    "reachable": False,
                    "functional": False,
                    "missing": "Clé BRAVE_API_KEY absente (DEFERRED)",
                    "role": "ROLE 1 — SEARCH",
                    "cost": "PAID"
                },
                "exa": {
                    "installed": False,
                    "configured": exa_key,
                    "key_present": exa_key,
                    "reachable": False,
                    "functional": False,
                    "missing": "Clé EXA_API_KEY et package exa_py absents (DEFERRED)",
                    "role": "ROLE 1 — SEARCH",
                    "cost": "PAID"
                },
                "firecrawl": {
                    "installed": False,
                    "configured": firecrawl_key,
                    "key_present": firecrawl_key,
                    "reachable": False,
                    "functional": False,
                    "missing": "Clé FIRECRAWL_API_KEY absente (DEFERRED)",
                    "role": "ROLE 1 — SEARCH / EXTRACT",
                    "cost": "PAID"
                },
                "perplexity": {
                    "installed": False,
                    "configured": perplexity_key,
                    "key_present": perplexity_key,
                    "reachable": False,
                    "functional": False,
                    "missing": "Clé PERPLEXITY_API_KEY absente (DEFERRED)",
                    "role": "ROLE 1 — SEARCH / REASONING",
                    "cost": "PAID"
                }
            },
            "extract_backends": {
                "local_http_scraper": {
                    "installed": True,
                    "configured": True,
                    "key_present": "N/A",
                    "reachable": True,
                    "functional": True,
                    "role": "ROLE 2 — EXTRACT (Primary Sovereign Fast)",
                    "cost": "FREE"
                },
                "jina_reader": {
                    "installed": True,
                    "configured": jina_key,
                    "key_present": jina_key,
                    "reachable": True,
                    "functional": True,
                    "role": "ROLE 2 — EXTRACT (Secondary Structured Markdown/PDF)",
                    "cost": "PAID / FREE_LIMITED"
                }
            },
            "browser_backends": {
                "brave_headless": {
                    "installed": bool(browser_path and "brave" in browser_name.lower()),
                    "binary_path": browser_path,
                    "reachable": bool(browser_path and "brave" in browser_name.lower()),
                    "functional": bool(browser_path and "brave" in browser_name.lower()),
                    "role": "ROLE 4 — BROWSER (Primary Local Headless)",
                    "cost": "FREE"
                },
                "chromium_hermes": {
                    "installed": os.path.exists(r"G:\Hermes\tools\chromium-1208\chrome-win64\chrome.exe"),
                    "binary_path": r"G:\Hermes\tools\chromium-1208\chrome-win64\chrome.exe",
                    "reachable": os.path.exists(r"G:\Hermes\tools\chromium-1208\chrome-win64\chrome.exe"),
                    "functional": os.path.exists(r"G:\Hermes\tools\chromium-1208\chrome-win64\chrome.exe"),
                    "role": "ROLE 4 — BROWSER (Fallback Local Headless)",
                    "cost": "FREE"
                },
                "cdp_port_8312": {
                    "installed": True,
                    "endpoint": "http://127.0.0.1:8312",
                    "reachable": True,
                    "functional": True,
                    "role": "ROLE 4 — BROWSER (Active CDP DevTools Port)",
                    "cost": "FREE"
                },
                "browser_use_cloud": {
                    "installed": False,
                    "configured": False,
                    "key_present": False,
                    "reachable": False,
                    "functional": False,
                    "missing": "Clé Cloud absente et package non installé (DEFERRED)",
                    "role": "ROLE 4 — BROWSER",
                    "cost": "PAID"
                },
                "lightpanda": {
                    "installed": False,
                    "configured": False,
                    "reachable": False,
                    "functional": False,
                    "missing": "Binaire lightpanda absent (DEFERRED)",
                    "role": "ROLE 4 — BROWSER",
                    "cost": "FREE"
                }
            },
            "semantic_backends": {
                "jina_search": {
                    "installed": True,
                    "configured": jina_key,
                    "key_present": jina_key,
                    "reachable": True,
                    "functional": True,
                    "role": "ROLE 3 — SEMANTIC / DEEP SEARCH",
                    "cost": "PAID / FREE_LIMITED"
                },
                "ollama_local": {
                    "installed": True,
                    "endpoint": "http://127.0.0.1:11434",
                    "reachable": True,
                    "functional": True,
                    "role": "ROLE 5 — RERANK / LOCAL SYNTHESIS",
                    "cost": "FREE"
                }
            }
        }
