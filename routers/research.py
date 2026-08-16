from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
import logging
import uuid

from core.evidence_store import EvidenceStore
from core.decision_router import DecisionRouter, SearchMode
from core.providers.tavily_provider import TavilyProvider
from core.providers.gemini_provider import GeminiProvider
from core.providers.ollama_provider import OllamaProvider

logger = logging.getLogger("ezzio.api.research")

router = APIRouter(prefix="/api/v1/research", tags=["Research"])

_evidence_store = EvidenceStore("runtime/evidence/evidence.db")
_decision_router = DecisionRouter([
    TavilyProvider(),
    GeminiProvider(),
    OllamaProvider()
])

async def init_research_router():
    """Initialise la base de persistance des preuves lors du lifespan."""
    await _evidence_store.init()
    logger.info("[OK] EvidenceStore initialisé pour le routeur Research.")

class ResearchRequest(BaseModel):
    query: str = Field(..., description="Requête de recherche ou d'investigation")
    mode: str = Field(default="fast", description="Mode de recherche : fast, deep, google, local")
    max_tokens: Optional[int] = Field(default=None, description="Limite de tokens")

class ResearchResponse(BaseModel):
    task_id: str
    mode: str
    provider: str
    data: Dict[str, Any] = Field(default_factory=dict)

@router.post("/search", response_model=ResearchResponse)
async def search_endpoint(payload: ResearchRequest):
    try:
        mode_map = {
            "fast": SearchMode.FAST,
            "deep": SearchMode.DEEP,
            "google": SearchMode.GOOGLE,
            "local": SearchMode.LOCAL
        }
        search_mode = mode_map.get(payload.mode.lower(), SearchMode.FAST)
        task_id = f"task_res_{uuid.uuid4().int >> 64}"

        result = await _decision_router.search(
            query=payload.query,
            mode=search_mode,
            max_tokens=payload.max_tokens or 400
        )

        provider_name = result.get("provider", "unknown")
        data_content = result.get("data", {})

        # Archivage transactionnel de la preuve
        await _evidence_store.store(
            query=payload.query,
            provider=provider_name,
            mode=payload.mode,
            data=data_content,
            task_id=task_id
        )

        return ResearchResponse(
            task_id=task_id,
            mode=payload.mode,
            provider=provider_name,
            data=data_content
        )
    except Exception as e:
        logger.error(f"[ERREUR] Échec /api/v1/research/search : {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
