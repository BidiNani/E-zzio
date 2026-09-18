"""Router /api/tools : liste des outils de recherche disponibles."""
from fastapi import APIRouter

router = APIRouter(tags=["tools"])


@router.get("/api/tools")
async def list_tools():
    """
    Liste tous les outils de recherche disponibles (Tavily, Jina, ...).
    Affiche leur statut : clé configurée, actif/inactif.
    """
    import os

    from core.secrets import load_secrets

    load_secrets()

    def _check_key(key_name: str) -> bool:
        v = os.getenv(key_name)
        return bool(v and v.strip())

    tools = [
        {
            "id": "tavily",
            "name": "Tavily",
            "category": "search",
            "description": "Recherche web IA optimisée pour les LLM",
            "key_configured": _check_key("TAVILY_API_KEY"),
            "enabled": _check_key("TAVILY_API_KEY"),
            "url": "https://tavily.com",
        },
        {
            "id": "jina",
            "name": "Jina AI",
            "category": "search",
            "description": "Scraping et lecture web structurée",
            "key_configured": _check_key("JINA_API_KEY"),
            "enabled": _check_key("JINA_API_KEY"),
            "url": "https://jina.ai",
        },
        {
            "id": "searxng",
            "name": "SearxNG",
            "category": "search",
            "description": "Méta-moteur privé (self-hosted)",
            "key_configured": _check_key("SEARXNG_URL"),
            "enabled": False,
            "url": "https://searxng.github.io",
        },
    ]

    return {
        "tools": tools,
        "summary": {
            "total": len(tools),
            "enabled": sum(1 for t in tools if t["enabled"]),
        }
    }