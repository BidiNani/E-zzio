"""
E-ZZIO Perception — RSS & Atom Feed Adapter.
Permet la veille technologique, sécuritaire (CVE) et le suivi de flux déterministe sans LLM :
1. Support des flux RSS 2.0 et Atom 1.0 via xml.etree / feedparser
2. Protection proactive contre le SSRF sur les URLs de flux
3. Filtrage par mot-clé et limitation du nombre d'articles
"""
from __future__ import annotations

import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from core.capabilities.capability_policy import CapabilityPolicy
from core.utils.http_pool import get_http_client

logger = logging.getLogger("RSSAdapter")


class RSSAdapter:
    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root)
        self.policy = CapabilityPolicy()

    def _is_safe_url(self, url: str) -> bool:
        """Vérifie la sécurité de l'URL contre les attaques SSRF."""
        try:
            parsed = urllib.parse.urlparse(url)
            hostname = (parsed.hostname or "").lower()
            if not hostname or hostname in ("localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254"):
                return False
            if hostname.startswith("192.168.") or hostname.startswith("10.") or hostname.startswith("172.16."):
                return False
            return parsed.scheme in ("http", "https")
        except Exception:
            return False

    async def fetch_feed(
        self,
        feed_url: str,
        limit: int = 10,
        keyword_filter: str | None = None
    ) -> dict[str, Any]:
        """Récupère et extrait les entrées structurées d'un flux RSS ou Atom."""
        if not self._is_safe_url(feed_url):
            return {
                "ok": False,
                "error": f"[SSRF-PROTECT] URL de flux non autorisée ou privée : {feed_url}"
            }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) E-ZzIO-RSS-Reader/2.0",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"
        }

        try:
            client = get_http_client()
            resp = await client.get(feed_url, headers=headers)
            if resp.status_code != 200:
                return {
                    "ok": False,
                    "status_code": resp.status_code,
                    "error": f"Échec HTTP lors de la récupération du flux : {resp.status_code}"
                }
            content = resp.text

            return self.parse_xml_feed(content, limit=limit, keyword_filter=keyword_filter, feed_url=feed_url)

        except Exception as exc:
            logger.error("[RSS-FETCH-ERROR] Erreur sur %s : %s", feed_url, exc)
            return {"ok": False, "error": str(exc)}

    def parse_xml_feed(
        self,
        xml_content: str,
        limit: int = 10,
        keyword_filter: str | None = None,
        feed_url: str = ""
    ) -> dict[str, Any]:
        """Parse le contenu XML (RSS ou Atom) de manière déterministe."""
        try:
            root = ET.fromstring(xml_content)
        except Exception as exc:
            return {"ok": False, "error": f"Format XML invalide : {exc}"}

        items: list[dict[str, Any]] = []

        # 1. Format RSS 2.0 (<channel><item>...</item></channel>)
        channel = root.find("channel")
        if channel is not None:
            feed_title = (channel.findtext("title") or "Flux RSS").strip()
            for item in channel.findall("item"):
                title = (item.findtext("title") or "Sans titre").strip()
                link = (item.findtext("link") or "").strip()
                desc = (item.findtext("description") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()

                # Nettoyage HTML dans la description
                clean_desc = re.sub(r"<[^>]+>", "", desc).strip()

                if keyword_filter and keyword_filter.lower() not in (title + " " + clean_desc).lower():
                    continue

                items.append({
                    "title": title,
                    "link": link,
                    "summary": clean_desc[:300],
                    "published": pub_date
                })
                if len(items) >= limit:
                    break

            return {
                "ok": True,
                "type": "rss_2.0",
                "feed_title": feed_title,
                "feed_url": feed_url,
                "count": len(items),
                "items": items
            }

        # 2. Format Atom (<feed><entry>...</entry></feed>)
        # Gestion des namespaces Atom
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        feed_title_node = root.find("atom:title", ns) or root.find("title")
        feed_title = feed_title_node.text.strip() if (feed_title_node is not None and feed_title_node.text) else "Flux Atom"

        entries = root.findall("atom:entry", ns) or root.findall("entry")
        for entry in entries:
            title_node = entry.find("atom:title", ns) or entry.find("title")
            title = title_node.text.strip() if (title_node is not None and title_node.text) else "Sans titre"

            link_node = entry.find("atom:link", ns) or entry.find("link")
            link = ""
            if link_node is not None:
                link = link_node.attrib.get("href", "") or (link_node.text or "")

            summary_node = entry.find("atom:summary", ns) or entry.find("summary") or entry.find("atom:content", ns) or entry.find("content")
            summary = summary_node.text.strip() if (summary_node is not None and summary_node.text) else ""
            clean_summary = re.sub(r"<[^>]+>", "", summary).strip()

            updated_node = entry.find("atom:updated", ns) or entry.find("updated") or entry.find("atom:published", ns) or entry.find("published")
            pub_date = updated_node.text.strip() if (updated_node is not None and updated_node.text) else ""

            if keyword_filter and keyword_filter.lower() not in (title + " " + clean_summary).lower():
                continue

            items.append({
                "title": title,
                "link": link,
                "summary": clean_summary[:300],
                "published": pub_date
            })
            if len(items) >= limit:
                break

        return {
            "ok": True,
            "type": "atom_1.0",
            "feed_title": feed_title,
            "feed_url": feed_url,
            "count": len(items),
            "items": items
        }


# Singleton global
rss_adapter = RSSAdapter()
