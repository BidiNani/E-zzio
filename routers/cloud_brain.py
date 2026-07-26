from fastapi import APIRouter
from pydantic import BaseModel

from core.cloud_brain_broker import status, providers, route, cloud_chat, hybrid_chat

router = APIRouter(tags=["cloud-brain"])

class RouteRequest(BaseModel):
    text: str
    provider: str = "auto"

class CloudChatRequest(BaseModel):
    text: str
    provider: str = "auto"
    system: str = ""
    use_cache: bool = True

class HybridChatRequest(BaseModel):
    text: str
    provider: str = "auto"
    force_cloud: bool = False

@router.get("/cloud-brain/status")
async def get_cloud_brain_status():
    return status()

@router.get("/cloud-brain/providers")
async def get_cloud_brain_providers():
    return providers()

@router.post("/cloud-brain/route")
async def post_cloud_brain_route(req: RouteRequest):
    return route(text=req.text, provider=req.provider)

@router.post("/api/chat/cloud")
async def post_api_chat_cloud(req: CloudChatRequest):
    return cloud_chat(text=req.text, provider=req.provider, system=req.system, use_cache=req.use_cache)

@router.post("/api/chat/hybrid")
async def post_api_chat_hybrid(req: HybridChatRequest):
    return hybrid_chat(text=req.text, provider=req.provider, force_cloud=req.force_cloud)
