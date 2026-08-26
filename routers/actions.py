from fastapi import APIRouter
from core.actions import toolbox
from core.schemas import CreateFileRequest

router = APIRouter(prefix="/actions", tags=["actions"])


@router.post("/create_file")
async def create_file(req: CreateFileRequest):
    return {"result": toolbox.create_file(req.filename, req.content)}


@router.get("/list_files")
async def list_files(path: str = "."):
    return {"result": toolbox.list_files(path)}


@router.get("/status")
async def actions_status():
    return toolbox.status()
