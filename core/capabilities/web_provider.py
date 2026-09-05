"""E-ZZIO Capability Router — Web Search & Structured Crawling Provider.

Unifies web capabilities behind CapabilityPolicy:
- web.search: Fast web search across authoritative sources (ALLOW)
- web.crawl: Structured Markdown extraction from target URLs (ALLOW)
- browser.automate: Interactive browser workflows (REQUIRE_HUMAN)

Zero vendor lock-in. Self-contained with direct HTTP transport and clean failovers.
"""
from __future__ import annotations
import os
import re
import logging
from typing import Dict, Any, List, Optional
import httpx

from core.capabilities.capability_policy import CapabilityPolicy, PolicyDecision
from core.utils.http_pool import get_http_client

logger = logging.getLogger("WebProvider")


class WebProvider:
    def __init__(self, searxng_url: Optional[str] = None):
        self.policy = CapabilityPolicy()
        self.searxng_url = searxng_url or os.environ.get("SEARXNG_URL")

    async def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Recherche web unifiée : SearXNG local (Tier 1) avec repli transparent sur DuckDuckGo (Tier 2)."""
        decision, reason = self.policy.evaluate_scope("web.search", {"query": query, "limit": limit})
        if decision != PolicyDecision.ALLOW:
            return {"ok": False, "error": reason}

        client = get_http_client()

        # 1. Tentative SearXNG si configuré
        if self.searxng_url:
            try:
                searx_endpoint = f"{self.searxng_url.rstrip('/')}/search"
                resp = await client.get(searx_endpoint, params={"q": query, "format": "json"})
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
                    return {
                        "ok": True,
                        "backend": "searxng",
                        "scope": "web.search",
                        "query": query,
                        "count": len(results),
                        "data": results
                    }
            except Exception as exc:
                logger.warning("[SEARXNG-WARN] Repli sur DuckDuckGo suite à : %s", exc)

        # 2. Requête de recherche DuckDuckGo HTML sans clé API (Souverain & Instantané)
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"q": query}
        
        try:
            r = await client.post(url, headers=headers, data=data)
            if r.status_code == 200:
                results = self._parse_ddg_html(r.text, limit=limit)
                return {
                    "ok": True,
                    "backend": "duckduckgo_html",
                    "scope": "web.search",
                    "query": query,
                    "count": len(results),
                    "data": results
                }
            return {"ok": False, "scope": "web.search", "status_code": r.status_code, "error": "Échec de recherche web"}
        except Exception as exc:
            logger.warning("[WEB-SEARCH-WARN] Erreur transport recherche web : %s", exc)
            return {"ok": False, "scope": "web.search", "error": str(exc)}

    def _parse_ddg_html(self, html: str, limit: int = 5) -> List[Dict[str, str]]:
        """Extrait les titres, URLs organiques et résumés des résultats HTML de recherche."""
        import urllib.parse
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

    async def crawl(self, target_url: str, max_chars: int = 4000) -> Dict[str, Any]:
        """Extrait le contenu textuel structuré en Markdown depuis une URL (scope: web.crawl)."""
        decision, reason = self.policy.evaluate_scope("web.crawl", {"url": target_url})
        if decision != PolicyDecision.ALLOW:
            return {"ok": False, "error": reason}

        # Protection SSRF proactive sur les adresses privées et cloud metadata
        import urllib.parse
        parsed = urllib.parse.urlparse(target_url)
        hostname = (parsed.hostname or "").lower()
        if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254") or hostname.startswith("192.168.") or hostname.startswith("10."):
            return {"ok": False, "error": f"[SSRF-PROTECT] Accès interdit à l'adresse interne/privée : {hostname}"}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) E-ZzIO-Crawler/2.0",
            "Accept": "text/html,application/xhtml+xml,text/plain"
        }
        try:
            client = get_http_client()
            r = await client.get(target_url, headers=headers)
            if r.status_code == 200:
                clean_markdown = self._html_to_markdown(r.text)
                truncated = clean_markdown[:max_chars]
                return {
                    "ok": True,
                    "scope": "web.crawl",
                    "url": target_url,
                    "length": len(truncated),
                    "content": truncated
                }
            return {"ok": False, "status_code": r.status_code, "error": f"HTTP {r.status_code}"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _html_to_markdown(self, html: str) -> str:
        """Convertit du HTML brut en texte/Markdown épuré sans tags parasites."""
        # Supprime scripts, styles, balises de navigation
        cleaned = re.sub(r'<(script|style|nav|footer|header)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
        # Convertit titres
        cleaned = re.sub(r'<h1[^>]*>(.*?)</h1>', r'\n# \1\n', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', cleaned, flags=re.DOTALL | re.IGNORECASE)
        # Convertit paragraphes et listes
        cleaned = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\1\n', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<li[^>]*>(.*?)</li>', r'\n- \1', cleaned, flags=re.DOTALL | re.IGNORECASE)
        # Supprime toutes les autres balises HTML
        cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
        # Nettoie les espaces multiples
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
        return cleaned.strip()
