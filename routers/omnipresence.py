from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from core.omnipresence import (
    discord_send_bot_channel,
    discord_send_webhook,
    inbox_add,
    load_config,
    messenger_send_text,
    mobile_pull,
    mobile_push,
    outbox_add,
    status,
    verify_mobile_token,
)

router = APIRouter(prefix="/omni", tags=["omnipresence"])


class TextMessage(BaseModel):
    text: str
    user: str = "local"
    source: str = "api"
    metadata: dict = {}


class OutboxMessage(BaseModel):
    target: str
    text: str
    metadata: dict = {}


class DiscordWebhookMessage(BaseModel):
    content: str
    username: str = "E-ZZIO"
    allow_send: bool | None = None


class DiscordBotMessage(BaseModel):
    content: str
    channel_id: str | None = None
    allow_send: bool | None = None


class MessengerTextMessage(BaseModel):
    text: str
    recipient_psid: str | None = None
    allow_send: bool | None = None


class MobilePushMessage(BaseModel):
    title: str = "E-ZZIO"
    text: str
    channel: str = "local"


@router.get("/status")
async def omni_status():
    return status()


@router.post("/inbox")
async def omni_inbox(req: TextMessage):
    return inbox_add(source=req.source, text=req.text, user=req.user, metadata=req.metadata)


@router.post("/outbox")
async def omni_outbox(req: OutboxMessage):
    return outbox_add(target=req.target, text=req.text, metadata=req.metadata)


@router.post("/discord/webhook")
async def omni_discord_webhook(req: DiscordWebhookMessage):
    return discord_send_webhook(content=req.content, username=req.username, allow_send=req.allow_send)


@router.post("/discord/bot/send")
async def omni_discord_bot_send(req: DiscordBotMessage):
    return discord_send_bot_channel(content=req.content, channel_id=req.channel_id, allow_send=req.allow_send)


@router.post("/messenger/send")
async def omni_messenger_send(req: MessengerTextMessage):
    return messenger_send_text(text=req.text, recipient_psid=req.recipient_psid, allow_send=req.allow_send)


@router.post("/mobile/push")
async def omni_mobile_push(req: MobilePushMessage):
    return mobile_push(title=req.title, text=req.text, channel=req.channel)


@router.get("/mobile/pull")
async def omni_mobile_pull(limit: int = 20):
    return mobile_pull(limit=limit)


@router.get("/messenger/webhook")
async def messenger_webhook_verify(request: Request):
    cfg = load_config()
    params = dict(request.query_params)

    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token and token == cfg.get("META_VERIFY_TOKEN"):
        return int(challenge) if str(challenge).isdigit() else challenge

    raise HTTPException(status_code=403, detail="Messenger verify token invalide.")


@router.post("/messenger/webhook")
async def messenger_webhook_receive(request: Request):
    payload = await request.json()
    return inbox_add(
        source="messenger.webhook",
        text="Messenger webhook received",
        user="meta",
        metadata=payload,
    )


@router.post("/mobile/inbox")
async def mobile_inbox(request: Request):
    token = request.headers.get("X-EZZIO-Mobile-Token", "")
    if not verify_mobile_token(token):
        raise HTTPException(status_code=403, detail="Token mobile invalide.")

    payload = await request.json()
    text = str(payload.get("text", ""))
    user = str(payload.get("user", "mobile"))
    metadata = payload.get("metadata", {})

    return inbox_add(source="mobile", text=text, user=user, metadata=metadata)
