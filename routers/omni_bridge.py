from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from core.omni_brain import (
    bridge_status,
    mobile_config,
    verify_mobile_token,
    local_brain_reply,
    available_commands,
    integration_truth,
)

router = APIRouter(prefix="/omni-bridge", tags=["omni-bridge"])


class OmniReplyRequest(BaseModel):
    text: str
    source: str = "api"
    user: str = "enrik"
    mode: str = "fast"


@router.get("/status")
async def omni_bridge_status():
    return bridge_status()


@router.get("/truth")
async def omni_bridge_truth():
    return integration_truth()


@router.get("/commands")
async def omni_bridge_commands():
    return available_commands()


@router.get("/mobile/config")
async def omni_mobile_config():
    return mobile_config()


@router.post("/reply")
async def omni_reply(req: OmniReplyRequest):
    return local_brain_reply(
        text=req.text,
        source=req.source,
        user=req.user,
        mode=req.mode,
    )


@router.post("/mobile/reply")
async def omni_mobile_reply(request: Request):
    token = request.headers.get("X-EZZIO-Mobile-Token", "")
    if not verify_mobile_token(token):
        raise HTTPException(status_code=403, detail="Token mobile invalide.")

    payload = await request.json()
    text = str(payload.get("text", ""))
    user = str(payload.get("user", "mobile"))
    mode = str(payload.get("mode", "fast"))

    return local_brain_reply(
        text=text,
        source="mobile",
        user=user,
        mode=mode,
    )
