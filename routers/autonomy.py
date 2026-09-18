from fastapi import APIRouter

from core.autonomy import doctor
from core.governor import tactical_plan
from core.schemas import Prompt

router = APIRouter(prefix="/autonomy", tags=["autonomy"])


@router.get("/status")
async def autonomy_status():
    return doctor()


@router.post("/doctor")
async def autonomy_doctor():
    return doctor()


@router.post("/plan")
async def autonomy_plan(prompt: Prompt):
    return tactical_plan(prompt.text)
