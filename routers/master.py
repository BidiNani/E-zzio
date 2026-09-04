from fastapi import APIRouter
from pydantic import BaseModel
from core.ezzio_master import ezzio_master
from routers.approval import router as approval_router
from routers.office import router as office_router

router = APIRouter(prefix="/master", tags=["E-ZZIO Master"])
router.include_router(approval_router)
router.include_router(office_router)



class MasterPrompt(BaseModel):
    text: str
    speed: str = "auto"
    force_cloud: bool = False


@router.post("/chat")
async def master_chat(prompt: MasterPrompt):
    result = await ezzio_master.execute_intent(prompt.text, speed=prompt.speed, force_cloud=prompt.force_cloud)
    return result
