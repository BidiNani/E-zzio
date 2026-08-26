from fastapi import APIRouter
from pydantic import BaseModel
from core.ezzio_master import ezzio_master

router = APIRouter(prefix="/master", tags=["E-ZZIO Master"])


class MasterPrompt(BaseModel):
    text: str
    speed: str = "auto"
    force_cloud: bool = False


@router.post("/chat")
async def master_chat(prompt: MasterPrompt):
    result = await ezzio_master.execute_intent(prompt.text, speed=prompt.speed, force_cloud=prompt.force_cloud)
    return result
