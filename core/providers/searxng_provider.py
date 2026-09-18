import logging

import httpx

from core.providers.iresearch_provider import IResearchProvider

logger = logging.getLogger("ezzio.providers.searxng")


class SearxngProvider(IResearchProvider):
    """Provider de recherche web souverain auto-hébergé via SearXNG."""
    name: str = "searxng"

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url

    async def search(self, query: str, max_results: int = 5) -> dict:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(f"{self.base_url}/search", params={"q": query, "format": "json"})
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])[:max_results]

                formatted_results = [{"title": r.get("title"), "url": r.get("url"), "content": r.get("content", "")} for r in results]

                text_summary = "\n".join([f"- [{r['title']}]({r['url']}): {r['content']}" for r in formatted_results])

                return {
                    "provider": "searxng",
                    "status": "success",
                    "data": {"text": text_summary or "Aucun résultat trouvé via SearXNG.", "results": formatted_results},
                }
        except Exception as e:
            logger.warning(f"[-] SearxngProvider indisponible ou en erreur : {e}")
            raise


# Alias de compatibilité pour les imports existants
class SearXNGProvider(SearxngProvider):
    """Alias de compatibilité haute casse pour les imports existants."""

    pass
