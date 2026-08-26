import re
import logging
import httpx
from typing import List, Optional

logger = logging.getLogger("ezzio.core.url_reader")


class UrlReader:
    """Extrait et nettoie le contenu textuel de n'importe quelle URL web."""

    URL_REGEX = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')

    @classmethod
    def extract_urls(cls, text: str) -> List[str]:
        """Extrait toutes les URLs présentes dans un texte."""
        return cls.URL_REGEX.findall(text)

    @classmethod
    async def fetch_url_content(cls, url: str) -> Optional[str]:
        """
        Récupère le contenu d'une URL.
        Utilise Jina Reader (r.jina.ai) pour transformer n'importe quelle page en Markdown propre,
        avec un fallback HTTP classique si besoin.
        """
        # Nettoyage de l'URL si elle commence par www.
        target_url = url if url.startswith("http") else f"https://{url}"

        # Jina Reader convertit instantanément n'importe quelle page web en Markdown LLM-friendly
        jina_endpoint = f"https://r.jina.ai/{target_url}"

        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            try:
                logger.info("[URL READER] Scraping de %s via Jina Reader...", target_url)
                resp = await client.get(jina_endpoint, headers={"Accept": "text/markdown", "User-Agent": "EzzioOS/49.3"})
                if resp.status_code == 200 and len(resp.text.strip()) > 50:
                    return resp.text
            except Exception as e:
                logger.warning("[URL READER] Échec Jina pour %s : %s. Tentative direct...", target_url, e)

            # Fallback : Requête HTTP directe
            try:
                resp = await client.get(target_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) EzzioOS"})
                if resp.status_code == 200:
                    return resp.text
            except Exception as e:
                logger.error("[URL READER] Erreur critique fetch URL %s : %s", target_url, e)

        return None
