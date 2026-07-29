from fastapi import APIRouter
from core.dispatcher import ezzio_dispatcher
from core.schemas import Prompt

router = APIRouter(tags=["chat"])

@router.post("/route")
async def route(prompt: Prompt):
    key, organ, score, hits = ezzio_dispatcher.select_organ(prompt.text)
    return {
        "selected_organ": key,
        "organ_label": organ["label"],
        "emotion": organ["emotion"],
        "talent": organ["talent"],
        "model": organ["model"],
        "fallback": organ["fallback"],
        "score": score,
        "hits": hits,
        "confidence": ezzio_dispatcher.confidence(score),
        "gpu_policy": "disabled_for_ezzio",
        "num_gpu": 0,
    }

@router.post("/chat")
async def chat(prompt: Prompt):
    return await ezzio_dispatcher.route_detailed_async(prompt.text, speed=prompt.speed)

@router.post("/api/chat")
async def api_chat(prompt: Prompt):
    return await ezzio_dispatcher.route_detailed_async(prompt.text, speed=prompt.speed)

@router.post("/api/chat/fast")
async def api_chat_fast(prompt: Prompt):
    return await ezzio_dispatcher.route_detailed_async(prompt.text, speed="fast")
