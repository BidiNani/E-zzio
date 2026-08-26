from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional

from core.ezzio_message_brain import handle_message, save_upload

router = APIRouter(tags=["ezzio-unified"])


class MessageJson(BaseModel):
    text: str = ""


@router.get("/api/ezzio/status")
async def status():
    return {
        "ok": True,
        "version": "v2.31-compact-real-assistant",
        "endpoint": "/api/ezzio/message",
        "features": ["chat", "vision_upload", "research_wikipedia", "system_intent"],
        "policy": {"cpu_ram_only": True, "gpu": "untouched", "no_ads": True},
    }


@router.post("/api/ezzio/message-json")
async def message_json(req: MessageJson):
    return handle_message(req.text)


@router.post("/api/ezzio/message")
async def message(text: str = Form(""), file: Optional[UploadFile] = File(None)):
    image_path = None
    if file is not None:
        content = await file.read()
        if content:
            image_path = str(save_upload(file.filename or "image.png", content))
    return handle_message(text, image_path)
