from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from runtime.core.ezzio_core import EzzioCore

router = APIRouter(prefix="/api/v1/chat", tags=["Autonomous Cognitive Chat"])

# Instance singleton du noyau Ezzio
_core = EzzioCore()

class ChatRequest(BaseModel):
    message: str = Field(..., description="Message ou prompt utilisateur")
    user_id: str = Field("default_user", description="Identifiant unique de l'utilisateur")
    session_id: Optional[str] = Field(None, description="Identifiant de session optionnel")

class ChatResponse(BaseModel):
    response: str
    intent: str
    provider: str
    mode: str
    session_id: str
    data: Dict[str, Any]

@router.on_event("startup")
async def startup_event():
    await _core.init()

@router.post("", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    try:
        result = await _core.think(
            user_id=req.user_id,
            message=req.message,
            session_id=req.session_id
        )
        return ChatResponse(
            response=result.get("response", ""),
            intent=result.get("intent", "unknown"),
            provider=result.get("provider", "unknown"),
            mode=result.get("mode", "unknown"),
            session_id=result.get("session_id", req.session_id or f"sess_{req.user_id}"),
            data=result.get("data", {})
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur d'inférence autonome: {str(exc)}")
