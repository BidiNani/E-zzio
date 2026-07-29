from fastapi import APIRouter
from core.dispatcher import ezzio_dispatcher
from core.schemas import Prompt

router = APIRouter(tags=["chat"])

@router.post("/route")
async def route(prompt: Prompt):
    speed = prompt.speed or "auto"
    if speed == "auto":
        speed = ezzio_dispatcher.auto_speed(prompt.text)

    key, organ, score, hits = ezzio_dispatcher.select_organ(prompt.text)
    selected_model = ezzio_dispatcher.select_model_for_speed(organ, speed)

    return {
        "selected_organ": key,
        "organ_label": organ["label"],
        "emotion": organ["emotion"],
        "talent": organ["talent"],
        "model": organ["model"],
        "fast_candidates": organ.get("fast_candidates", []),
        "deep_model": organ.get("deep_model"),
        "selected_model": selected_model,
        "fallbacks": ezzio_dispatcher.select_fallbacks_for_speed(organ, speed, selected_model),
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

@router.post("/api/chat/auto")
async def api_chat_auto(prompt: Prompt):
    return await ezzio_dispatcher.route_detailed_async(prompt.text, speed="auto")

@router.post("/api/chat/fast")
async def api_chat_fast(prompt: Prompt):
    return await ezzio_dispatcher.route_detailed_async(prompt.text, speed="fast")

@router.post("/api/chat/deep")
async def api_chat_deep(prompt: Prompt):
    return await ezzio_dispatcher.route_detailed_async(prompt.text, speed="deep")
