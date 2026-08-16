from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
import logging

from runtime.core.ezzio_core import EzzioCore
from core.memory.unified_gateway import UnifiedMemoryGateway

logger = logging.getLogger("ezzio.api.chat")

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])

# Instance mémoire et noyau EzzioCore
_memory_gateway = UnifiedMemoryGateway("runtime/evidence/evidence.db")
_core = EzzioCore(memory_gateway=_memory_gateway)

async def init_chat_router():
    """Initialise le sous-système de chat lors du lifespan de l'application."""
    await _core.init()
    logger.info("[OK] EzzioCore et MemoryGateway initialisés pour le routeur Chat.")

class ChatRequest(BaseModel):
    message: str = Field(..., description="Message de l'utilisateur")
    user_id: str = Field(default="user_default", description="Identifiant unique utilisateur")
    session_id: Optional[str] = Field(default=None, description="Identifiant de session de conversation")

class ChatResponse(BaseModel):
    response: str
    intent: str
    provider: str
    mode: str
    session_id: str
    data: Dict[str, Any] = Field(default_factory=dict)

@router.post("", response_model=ChatResponse)
async def post_chat(payload: ChatRequest):
    try:
        result = await _core.think(
            user_id=payload.user_id,
            message=payload.message,
            session_id=payload.session_id
        )
        return ChatResponse(
            response=result.get("response", ""),
            intent=result.get("intent", "local_chat"),
            provider=result.get("provider", "ollama"),
            mode=result.get("mode", "local_chat"),
            session_id=result.get("session_id", f"sess_{payload.user_id}"),
            data=result.get("data", {})
        )
    except Exception as e:
        logger.error(f"[ERREUR] Échec /api/v1/chat : {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
