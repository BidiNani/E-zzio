from fastapi import APIRouter
from pydantic import BaseModel

from core.human_loop import (
    status,
    perceive,
    reflect,
    tick,
    journal_tail,
    load_memory,
    save_memory,
)

router = APIRouter(prefix="/human", tags=["human-loop"])

class PerceiveRequest(BaseModel):
    context: str = ""

class ReflectRequest(BaseModel):
    note: str = ""

class TickRequest(BaseModel):
    goal: str = ""
    context: str = ""
    execute: bool = True

class MemoryPatchRequest(BaseModel):
    learned_preference: str = ""

@router.get("/status")
async def get_human_status():
    return status()

@router.post("/perceive")
async def post_human_perceive(req: PerceiveRequest):
    return perceive(context=req.context)

@router.post("/reflect")
async def post_human_reflect(req: ReflectRequest):
    return reflect(note=req.note)

@router.post("/tick")
async def post_human_tick(req: TickRequest):
    return tick(user_goal=req.goal, context=req.context, execute=req.execute)

@router.get("/journal")
async def get_human_journal(limit: int = 20):
    return journal_tail(limit=limit)

@router.get("/memory")
async def get_human_memory():
    return {
        "ok": True,
        "memory": load_memory(),
    }

@router.post("/memory/preference")
async def post_human_memory_preference(req: MemoryPatchRequest):
    memory = load_memory()
    preference = req.learned_preference.strip()

    if preference:
        memory.setdefault("learned_preferences", [])
        if preference not in memory["learned_preferences"]:
            memory["learned_preferences"].append(preference)
            save_memory(memory)

    return {
        "ok": True,
        "memory": memory,
    }
