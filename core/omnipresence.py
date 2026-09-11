import os
import json
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from dotenv import dotenv_values

PROJECT_ROOT = Path("G:/AI/E-zzio")
SECRETS_FILE = PROJECT_ROOT / "secrets" / "omnipresence.env"
BRIDGE_ROOT = PROJECT_ROOT / "bridge"
INBOX = BRIDGE_ROOT / "inbox"
OUTBOX = BRIDGE_ROOT / "outbox"
MOBILE = BRIDGE_ROOT / "mobile"
DISCORD_DIR = BRIDGE_ROOT / "discord"
MESSENGER_DIR = BRIDGE_ROOT / "messenger"

for p in [INBOX, OUTBOX, MOBILE, DISCORD_DIR, MESSENGER_DIR]:
    p.mkdir(parents=True, exist_ok=True)

CPU_ONLY_ENV = {
    "OLLAMA_NUM_GPU": "0",
    "CUDA_VISIBLE_DEVICES": "",
    "GGML_CUDA": "0",
    "CUDA_DEVICE_ORDER": "PCI_BUS_ID",
    "EZZIO_GPU_POLICY": "cpu_ram_only",
    "EZZIO_NUM_GPU": "0",
    "PYTORCH_ENABLE_MPS_FALLBACK": "0",
}

for key, value in CPU_ONLY_ENV.items():
    os.environ[key] = value


def load_config() -> Dict[str, str]:
    cfg = {}
    if SECRETS_FILE.exists():
        cfg.update({k: str(v or "") for k, v in dotenv_values(SECRETS_FILE).items()})
    for key in [
        "DISCORD_WEBHOOK_URL",
        "DISCORD_BOT_TOKEN",
        "DISCORD_DEFAULT_CHANNEL_ID",
        "META_PAGE_ACCESS_TOKEN",
        "META_PAGE_ID",
        "META_VERIFY_TOKEN",
        "META_DEFAULT_RECIPIENT_PSID",
        "EZZIO_MOBILE_SHARED_TOKEN",
        "EZZIO_BRIDGE_ALLOW_SEND",
        "EZZIO_BRIDGE_LOG_PAYLOADS",
    ]:
        cfg[key] = os.environ.get(key, cfg.get(key, ""))
    return cfg


def _redact(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return value[:4] + "..." + value[-4:]


def _bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in ["1", "true", "yes", "y", "on"]


def now_stamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def write_event(kind: str, payload: Dict[str, Any], folder: Path = OUTBOX) -> Dict[str, Any]:
    event_id = f"{now_stamp()}_{uuid.uuid4().hex[:10]}"
    record = {
        "id": event_id,
        "kind": kind,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": payload,
    }
    path = folder / f"{event_id}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "id": event_id, "path": str(path), "record": record}


def status() -> Dict[str, Any]:
    cfg = load_config()
    return {
        "version": "v2.11-omnipresence-hub",
        "policy": {
            "cpu_ram_only": True,
            "gpu": "untouched",
            "scraping": "forbidden",
            "discord": "official bot/webhook only",
            "messenger": "official Meta Page Messenger Platform only",
            "send_default": "disabled unless EZZIO_BRIDGE_ALLOW_SEND=true",
        },
        "paths": {
            "bridge": str(BRIDGE_ROOT),
            "inbox": str(INBOX),
            "outbox": str(OUTBOX),
            "mobile": str(MOBILE),
            "discord": str(DISCORD_DIR),
            "messenger": str(MESSENGER_DIR),
            "secrets": str(SECRETS_FILE),
        },
        "config": {
            "discord_webhook_configured": bool(cfg.get("DISCORD_WEBHOOK_URL")),
            "discord_bot_configured": bool(cfg.get("DISCORD_BOT_TOKEN")),
            "discord_default_channel_id": _redact(cfg.get("DISCORD_DEFAULT_CHANNEL_ID", "")),
            "meta_page_token_configured": bool(cfg.get("META_PAGE_ACCESS_TOKEN")),
            "meta_page_id": _redact(cfg.get("META_PAGE_ID", "")),
            "meta_default_recipient_psid": _redact(cfg.get("META_DEFAULT_RECIPIENT_PSID", "")),
            "mobile_token_configured": bool(cfg.get("EZZIO_MOBILE_SHARED_TOKEN")),
            "send_enabled": _bool(cfg.get("EZZIO_BRIDGE_ALLOW_SEND", "false")),
        },
    }


def inbox_add(source: str, text: str, user: str = "unknown", metadata: Optional[Dict[str, Any]] = None):
    payload = {
        "source": source,
        "user": user,
        "text": text,
        "metadata": metadata or {},
    }
    return write_event("inbox.message", payload, INBOX)


def outbox_add(target: str, text: str, metadata: Optional[Dict[str, Any]] = None):
    payload = {
        "target": target,
        "text": text,
        "metadata": metadata or {},
    }
    return write_event("outbox.message", payload, OUTBOX)


def discord_send_webhook(content: str, username: str = "E-ZZIO", allow_send: Optional[bool] = None):
    cfg = load_config()
    webhook = cfg.get("DISCORD_WEBHOOK_URL", "").strip()

    if allow_send is None:
        allow_send = _bool(cfg.get("EZZIO_BRIDGE_ALLOW_SEND", "false"))

    event = outbox_add("discord.webhook", content, {"username": username, "send_enabled": allow_send})

    if not webhook:
        return {
            "ok": False,
            "dry_run": True,
            "error": "DISCORD_WEBHOOK_URL non configuré.",
            "event": event,
        }

    if not allow_send:
        return {
            "ok": True,
            "dry_run": True,
            "message": "Envoi Discord simulé. Mets EZZIO_BRIDGE_ALLOW_SEND=true pour envoyer réellement.",
            "event": event,
        }

    r = requests.post(
        webhook,
        json={"content": content, "username": username},
        timeout=20,
    )

    return {
        "ok": r.status_code < 400,
        "status_code": r.status_code,
        "response": r.text[:1000],
        "event": event,
    }


def discord_send_bot_channel(content: str, channel_id: Optional[str] = None, allow_send: Optional[bool] = None):
    cfg = load_config()
    token = cfg.get("DISCORD_BOT_TOKEN", "").strip()
    channel_id = channel_id or cfg.get("DISCORD_DEFAULT_CHANNEL_ID", "").strip()

    if allow_send is None:
        allow_send = _bool(cfg.get("EZZIO_BRIDGE_ALLOW_SEND", "false"))

    event = outbox_add("discord.bot.channel", content, {"channel_id": _redact(channel_id), "send_enabled": allow_send})

    if not token or not channel_id:
        return {
            "ok": False,
            "dry_run": True,
            "error": "DISCORD_BOT_TOKEN ou DISCORD_DEFAULT_CHANNEL_ID manquant.",
            "event": event,
        }

    if not allow_send:
        return {
            "ok": True,
            "dry_run": True,
            "message": "Envoi Discord bot simulé. Mets EZZIO_BRIDGE_ALLOW_SEND=true pour envoyer réellement.",
            "event": event,
        }

    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    r = requests.post(
        url,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "E-ZZIO-Omnipresence/2.11",
        },
        json={"content": content},
        timeout=20,
    )

    return {
        "ok": r.status_code < 400,
        "status_code": r.status_code,
        "response": r.text[:2000],
        "event": event,
    }


def messenger_send_text(text: str, recipient_psid: Optional[str] = None, allow_send: Optional[bool] = None):
    cfg = load_config()
    token = cfg.get("META_PAGE_ACCESS_TOKEN", "").strip()
    recipient_psid = recipient_psid or cfg.get("META_DEFAULT_RECIPIENT_PSID", "").strip()

    if allow_send is None:
        allow_send = _bool(cfg.get("EZZIO_BRIDGE_ALLOW_SEND", "false"))

    event = outbox_add("messenger.text", text, {"recipient_psid": _redact(recipient_psid), "send_enabled": allow_send})

    if not token or not recipient_psid:
        return {
            "ok": False,
            "dry_run": True,
            "error": "META_PAGE_ACCESS_TOKEN ou META_DEFAULT_RECIPIENT_PSID manquant.",
            "event": event,
        }

    if not allow_send:
        return {
            "ok": True,
            "dry_run": True,
            "message": "Envoi Messenger simulé. Mets EZZIO_BRIDGE_ALLOW_SEND=true pour envoyer réellement.",
            "event": event,
        }

    url = "https://graph.facebook.com/v20.0/me/messages"
    payload = {
        "recipient": {"id": recipient_psid},
        "message": {"text": text},
        "messaging_type": "RESPONSE",
    }

    r = requests.post(
        url,
        params={"access_token": token},
        json=payload,
        timeout=20,
    )

    return {
        "ok": r.status_code < 400,
        "status_code": r.status_code,
        "response": r.text[:2000],
        "event": event,
    }


def mobile_push(text: str, title: str = "E-ZZIO", channel: str = "local"):
    payload = {
        "title": title,
        "text": text,
        "channel": channel,
        "note": "Bridge local prêt pour futur smartphone/app/APK.",
    }
    return write_event("mobile.push", payload, MOBILE)


def mobile_pull(limit: int = 20):
    limit = max(1, min(int(limit), 100))
    files = sorted(MOBILE.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    out = []
    for p in files:
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            out.append({"path": str(p), "error": "json invalid"})
    return {"ok": True, "items": out}


def verify_mobile_token(token: str):
    cfg = load_config()
    expected = cfg.get("EZZIO_MOBILE_SHARED_TOKEN", "")
    return bool(expected and token and token == expected)
