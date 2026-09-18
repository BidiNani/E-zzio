from fastapi import APIRouter
from pydantic import BaseModel

from core.pc_commander import command, interpret, status

router = APIRouter(tags=["pc-commander"])


class InterpretRequest(BaseModel):
    text: str


class CommanderRequest(BaseModel):
    text: str
    session: str = "pc"


@router.get("/commander/status")
async def get_commander_status():
    return status()


@router.post("/commander/interpret")
async def post_commander_interpret(req: InterpretRequest):
    return {
        "ok": True,
        "interpretation": interpret(req.text),
    }


@router.post("/commander/command")
async def post_commander_command(req: CommanderRequest):
    return command(text=req.text, session=req.session)


@router.post("/api/chat/commander")
async def post_api_chat_commander(req: CommanderRequest):
    return command(text=req.text, session=req.session)
