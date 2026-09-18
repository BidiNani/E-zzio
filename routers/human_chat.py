from fastapi import APIRouter
from pydantic import BaseModel

from core.human_chat import (
    build_brief,
    human_chat,
    list_sessions,
    read_session,
    status,
)

router = APIRouter(tags=["human-chat"])


class HumanChatRequest(BaseModel):
    text: str
    session: str = "pc"
    task: str = "auto"
    speed: str = "auto"
    predict: int = 260


@router.get("/human-chat/status")
async def get_human_chat_status():
    return status()


@router.get("/human-chat/sessions")
async def get_human_chat_sessions():
    return list_sessions()


@router.get("/human-chat/session/{session}")
async def get_human_chat_session(session: str, limit: int = 30):
    return {
        "ok": True,
        "session": session,
        "events": read_session(session, limit=limit),
    }


@router.get("/human-chat/brief")
async def get_human_chat_brief():
    return build_brief()


@router.post("/api/chat/human")
async def post_api_chat_human(req: HumanChatRequest):
    return human_chat(
        text=req.text,
        session=req.session,
        task=req.task,
        speed=req.speed,
        predict=req.predict,
    )


@router.post("/human-chat/message")
async def post_human_chat_message(req: HumanChatRequest):
    return human_chat(
        text=req.text,
        session=req.session,
        task=req.task,
        speed=req.speed,
        predict=req.predict,
    )
