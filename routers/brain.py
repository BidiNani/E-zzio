from fastapi import APIRouter
from pydantic import BaseModel

from core.pc_model_router import (
    chat_with_route,
    router_status,
    select_model,
    write_default_policy,
)

router = APIRouter(prefix="/brain", tags=["brain"])


class RouteRequest(BaseModel):
    text: str = ""
    task: str = "auto"
    speed: str = "auto"


class BrainChatRequest(BaseModel):
    text: str
    task: str = "auto"
    speed: str = "auto"
    predict: int = 260


@router.get("/status")
async def brain_get_status():
    return router_status()


@router.post("/route")
async def brain_post_route(req: RouteRequest):
    return select_model(task=req.task, text=req.text, speed=req.speed)


@router.post("/chat")
async def brain_post_chat(req: BrainChatRequest):
    return chat_with_route(
        text=req.text,
        task=req.task,
        speed=req.speed,
        predict=req.predict,
    )


@router.post("/policy/default")
async def brain_post_policy_default():
    return write_default_policy()
