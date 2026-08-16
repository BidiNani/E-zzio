from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from runtime.model_router import EzzioModelRouter, ModelRequest

router = APIRouter(prefix="/api/llm", tags=["llm"])
model_orchestrator = EzzioModelRouter()

class GenerateDTO(BaseModel):
    prompt: str
    task: str = "general"
    complexity: str = "low"
    latency: str = "normal"
    budget: str = "local_first"
    system_prompt: Optional[str] = None
    agent_id: str = "web_api"

@router.post("/generate")
def generate_text(payload: GenerateDTO):
    try:
        req = ModelRequest(
            prompt=payload.prompt,
            task=payload.task,
            complexity=payload.complexity,
            latency=payload.latency,
            budget=payload.budget,
            system_prompt=payload.system_prompt
        )
        response = model_orchestrator.generate(req, agent_id=payload.agent_id)
        return {
            "ok": True,
            "content": response.get("response", ""),
            "model_used": response.get("model_used"),
            "provider_used": response.get("provider_used"),
            "latency_ms": response.get("latency_ms", 0),
            "fallback_applied": False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


