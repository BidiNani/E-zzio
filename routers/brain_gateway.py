from fastapi import APIRouter
from pydantic import BaseModel

from core.pc_model_router import (
    router_status,
    select_model,
    chat_with_route,
)

router = APIRouter(tags=["brain-gateway"])


class GatewayRouteRequest(BaseModel):
    text: str = ""
    task: str = "auto"
    speed: str = "auto"


class GatewayChatRequest(BaseModel):
    text: str
    task: str = "auto"
    speed: str = "auto"
    predict: int = 260


@router.get("/api/brain/status")
async def api_brain_status():
    data = router_status()
    data["gateway"] = {
        "ok": True,
        "version": "v2.17-pc-brain-gateway",
        "aliases": [
            "/api/brain/chat",
            "/api/chat/pc",
            "/api/chat/router",
        ],
    }
    return data


@router.post("/api/brain/route")
async def api_brain_route(req: GatewayRouteRequest):
    return select_model(task=req.task, text=req.text, speed=req.speed)


@router.post("/api/brain/chat")
async def api_brain_chat(req: GatewayChatRequest):
    data = chat_with_route(
        text=req.text,
        task=req.task,
        speed=req.speed,
        predict=req.predict,
    )
    data["gateway"] = "/api/brain/chat"
    return data


@router.post("/api/chat/pc")
async def api_chat_pc(req: GatewayChatRequest):
    data = chat_with_route(
        text=req.text,
        task=req.task,
        speed=req.speed,
        predict=req.predict,
    )
    data["gateway"] = "/api/chat/pc"
    return data


@router.post("/api/chat/router")
async def api_chat_router(req: GatewayChatRequest):
    data = chat_with_route(
        text=req.text,
        task=req.task,
        speed=req.speed,
        predict=req.predict,
    )
    data["gateway"] = "/api/chat/router"
    return data
