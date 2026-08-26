import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from runtime.rss.cache import RSSCacheStore


class RSSCollector:
    """Collector supporting RSS 2.0 and Atom with namespace handling."""

    def __init__(self, cache_store: Optional[RSSCacheStore] = None):
        self.cache = cache_store or RSSCacheStore()
        self.atom_ns = "{http://www.w3.org/2005/Atom}"

    def _extract_text(self, element, tag_name: str) -> str:
        if element is None:
            return ""
        el = element.find(tag_name)
        if el is None:
            el = element.find(f"{self.atom_ns}{tag_name}")

        if el is not None:
            if tag_name == "link":
                return el.get("href", "").strip() or (el.text.strip() if el.text else "")
            return el.text.strip() if el.text else ""
        return ""

    def parse_xml(self, xml_data: bytes) -> List[Dict[str, Any]]:
        articles = []
        root = ET.fromstring(xml_data)

        items = root.findall(".//item")
        if not items:
            items = root.findall(f".//{self.atom_ns}entry")

        for item in items:
            title = self._extract_text(item, "title") or "Untitled"
            link = self._extract_text(item, "link")
            guid = self._extract_text(item, "guid") or self._extract_text(item, "id") or link or title
            summary = self._extract_text(item, "description") or self._extract_text(item, "summary") or self._extract_text(item, "content")
            published_at = (
                self._extract_text(item, "pubDate") or self._extract_text(item, "published") or self._extract_text(item, "updated")
            )

            article = {"guid": guid, "title": title, "link": link, "summary": summary[:500], "published_at": published_at}
            articles.append(article)
            self.cache.save_article(guid, title, link, summary[:500], published_at)

        return articles

    def fetch_and_parse(self, feed_url: str) -> List[Dict[str, Any]]:
        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": "E-ZZIO-CognitiveAgent/2.5"})
            with urllib.request.urlopen(req, timeout=5) as response:
                return self.parse_xml(response.read())
        except Exception as e:
            print(f"[!] Erreur de collecte RSS pour {feed_url}: {e}")
            return []
