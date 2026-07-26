from fastapi import APIRouter
from core.dispatcher import ezzio_dispatcher
from core.schemas import Prompt

router = APIRouter(tags=["chat"])

@router.post("/preflight")
async def preflight(prompt: Prompt):
    return ezzio_dispatcher.preflight(prompt.text, speed=prompt.speed)

@router.post("/route")
async def route(prompt: Prompt):
    return ezzio_dispatcher.preflight(prompt.text, speed=prompt.speed)

@router.post("/chat")
async def chat(prompt: Prompt):
    return await ezzio_dispatcher.route_detailed_async(prompt.text, speed=prompt.speed)

@router.post("/api/chat")
async def api_chat(prompt: Prompt):
    return await ezzio_dispatcher.route_detailed_async(prompt.text, speed=prompt.speed)

@router.post("/api/chat/auto")
async def api_chat_auto(prompt: Prompt):
    return await ezzio_dispatcher.route_detailed_async(prompt.text, speed="auto")

@router.post("/api/chat/fast")
async def api_chat_fast(prompt: Prompt):
    return await ezzio_dispatcher.route_detailed_async(prompt.text, speed="fast")

@router.post("/api/chat/deep")
async def api_chat_deep(prompt: Prompt):
    return await ezzio_dispatcher.route_detailed_async(prompt.text, speed="deep")
