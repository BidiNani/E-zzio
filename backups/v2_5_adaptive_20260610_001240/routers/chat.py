from fastapi import APIRouter
from core.dispatcher import ezzio_dispatcher
from core.schemas import Prompt

router = APIRouter(tags=["chat"])

@router.post("/route")
async def route(prompt: Prompt):
    key, organ, score, hits = ezzio_dispatcher.select_organ(prompt.text)
    speed = prompt.speed or "normal"
    return {
        "selected_organ": key,
        "organ_label": organ["label"],
        "emotion": organ["emotion"],
        "talent": organ["talent"],
        "model": organ["model"],
        "fast_model": organ.get("fast_model"),
        "deep_model": organ.get("deep_model"),
        "selected_model": ezzio_dispatcher.select_model_for_speed(organ, speed),
        "fallback": ezzio_dispatcher.select_fallback_for_speed(organ, speed),
        "speed": speed,
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

@router.post("/api/chat/deep")
async def api_chat_deep(prompt: Prompt):
    return await ezzio_dispatcher.route_detailed_async(prompt.text, speed="deep")
