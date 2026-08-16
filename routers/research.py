from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from core.decision_router import DecisionRouter, SearchMode
from core.evidence_store import EvidenceStore
from core.skills.research_skill import ResearchSkill
from core.providers.tavily_provider import TavilyProvider
from core.providers.jina_provider import JinaProvider
from core.providers.gemini_provider import GeminiProvider

router = APIRouter(prefix="/api/v1/research", tags=["Research & Intelligence"])

# Initialisation singleton des composants
_tavily = TavilyProvider()
_jina = JinaProvider()
_gemini = GeminiProvider()
_evidence_store = EvidenceStore("runtime/evidence/evidence.db")
_decision_router = DecisionRouter(providers=[_tavily, _jina, _gemini])
_research_skill = ResearchSkill(
    router=_decision_router,
    evidence_store=_evidence_store
)

class ResearchRequest(BaseModel):
    query: str = Field(..., description="Requête de recherche ou prompt d'analyse")
    mode: str = Field("fast", description="Mode de recherche : fast, research, forensic, google")
    task_id: Optional[str] = Field(None, description="Identifiant optionnel de tâche gouvernée")

class ResearchResponse(BaseModel):
    task_id: str
    mode: str
    provider: str
    data: Dict[str, Any]

@router.on_event("startup")
async def startup_event():
    await _evidence_store.init()

@router.post("/search", response_model=ResearchResponse)
async def perform_search(req: ResearchRequest):
    mode_mapping = {
        "fast": SearchMode.FAST,
        "research": SearchMode.RESEARCH,
        "forensic": SearchMode.FORENSIC,
        "google": SearchMode.GOOGLE,
    }
    selected_mode = mode_mapping.get(req.mode.lower(), SearchMode.FAST)
    effective_task_id = req.task_id or f"task_res_{id(req)}"
    
    try:
        # Appel de la méthode search() de ResearchSkill
        result = await _research_skill.search(
            query=req.query,
            mode=selected_mode,
            task_id=effective_task_id
        )
        return ResearchResponse(
            task_id=effective_task_id,
            mode=result.get("mode", req.mode),
            provider=result.get("provider", "unknown"),
            data=result.get("data", {})
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur d'orchestration de recherche: {str(exc)}")
