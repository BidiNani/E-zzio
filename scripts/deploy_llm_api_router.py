from pathlib import Path

ROOT = Path(r"G:\AI\E-zzio")
ROUTERS_DIR = ROOT / "runtime" / "routers"
ROUTERS_DIR.mkdir(parents=True, exist_ok=True)

llm_router_code = """from fastapi import APIRouter, HTTPException
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
            "content": response.content,
            "model_used": response.model_used,
            "provider_used": response.provider_used,
            "latency_ms": response.latency_ms,
            "fallback_applied": response.fallback_applied
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
"""

(ROUTERS_DIR / "llm.py").write_text(llm_router_code, encoding="utf-8")
print("[OK] Routeur API HTTP runtime/routers/llm.py déployé.")
