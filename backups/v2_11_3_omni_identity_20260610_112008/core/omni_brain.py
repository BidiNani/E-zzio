import os
import json
import time
import uuid
import socket
from pathlib import Path
from typing import Optional, Dict, Any

import ollama
from dotenv import dotenv_values

PROJECT_ROOT = Path("G:/AI/E-zzio")
SECRETS_FILE = PROJECT_ROOT / "secrets" / "omnipresence.env"
BRIDGE_ROOT = PROJECT_ROOT / "bridge"
INBOX = BRIDGE_ROOT / "inbox"
OUTBOX = BRIDGE_ROOT / "outbox"
MOBILE = BRIDGE_ROOT / "mobile"
BRAIN_LOGS = BRIDGE_ROOT / "brain"

for p in [INBOX, OUTBOX, MOBILE, BRAIN_LOGS]:
    p.mkdir(parents=True, exist_ok=True)

CPU_ONLY_ENV = {
    "OLLAMA_NUM_GPU": "0",
    "CUDA_VISIBLE_DEVICES": "",
    "GGML_CUDA": "0",
    "CUDA_DEVICE_ORDER": "PCI_BUS_ID",
    "EZZIO_GPU_POLICY": "cpu_ram_only",
    "EZZIO_NUM_GPU": "0",
    "PYTORCH_ENABLE_MPS_FALLBACK": "0",
    "EZZIO_NO_ADS": "true",
    "EZZIO_NO_TRACKING": "true",
    "EZZIO_NO_SPONSORS": "true",
}

for key, value in CPU_ONLY_ENV.items():
    os.environ[key] = value

FAST_MODEL = "qwen3:1.7b"
COMPANION_MODEL = "hermes3:8b"

def load_config() -> Dict[str, str]:
    cfg = {}
    if SECRETS_FILE.exists():
        cfg.update({k: str(v or "") for k, v in dotenv_values(SECRETS_FILE).items()})
    for key in [
        "EZZIO_MOBILE_SHARED_TOKEN",
        "EZZIO_BRIDGE_ALLOW_SEND",
        "EZZIO_NO_ADS",
        "EZZIO_NO_TRACKING",
        "EZZIO_NO_SPONSORS",
    ]:
        cfg[key] = os.environ.get(key, cfg.get(key, ""))
    return cfg

def _bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in ["1", "true", "yes", "y", "on"]

def _redact(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 10:
        return "***"
    return value[:5] + "..." + value[-5:]

def get_lan_ips():
    ips = []
    try:
        host = socket.gethostname()
        for item in socket.getaddrinfo(host, None):
            ip = item[4][0]
            if "." in ip and not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass

    # fallback socket UDP sans envoyer réellement de payload utile
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127.") and ip not in ips:
            ips.append(ip)
    except Exception:
        pass

    return ips

def mobile_config():
    cfg = load_config()
    ips = get_lan_ips()
    token = cfg.get("EZZIO_MOBILE_SHARED_TOKEN", "")

    urls = []
    for ip in ips:
        urls.append({
            "host": ip,
            "base_url": f"http://{ip}:8000",
            "status": f"http://{ip}:8000/status",
            "mobile_pull": f"http://{ip}:8000/omni/mobile/pull",
            "mobile_inbox": f"http://{ip}:8000/omni/mobile/inbox",
            "omni_reply": f"http://{ip}:8000/omni-bridge/reply",
        })

    return {
        "ok": True,
        "name": "E-ZZIO Mobile Bridge",
        "policy": {
            "local_wifi_only": True,
            "token_required": True,
            "ads": "forbidden",
            "tracking": "forbidden",
            "gpu": "untouched",
        },
        "urls": urls,
        "token_preview": _redact(token),
        "headers": {
            "X-EZZIO-Mobile-Token": "<ton token dans secrets/omnipresence.env>"
        },
        "note": "Pour smartphone : démarre scripts/start_ezzio_lan.ps1, puis utilise l'URL LAN depuis le même Wi-Fi.",
    }

def verify_mobile_token(token: str):
    expected = load_config().get("EZZIO_MOBILE_SHARED_TOKEN", "")
    return bool(expected and token and token == expected)

def write_json_event(folder: Path, kind: str, payload: Dict[str, Any]):
    event_id = f"{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:10]}"
    record = {
        "id": event_id,
        "kind": kind,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": payload,
    }
    path = folder / f"{event_id}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "id": event_id, "path": str(path), "record": record}

def local_brain_reply(text: str, source: str = "mobile", user: str = "enrik", mode: str = "fast"):
    text = str(text or "").strip()

    if not text:
        return {
            "ok": False,
            "error": "Message vide.",
        }

    inbox = write_json_event(INBOX, "omni.inbox", {
        "source": source,
        "user": user,
        "text": text,
        "mode": mode,
    })

    model = FAST_MODEL if mode != "companion" else COMPANION_MODEL

    system = """
Tu es E-ZZIO, l'ami IA local d'Enrik.
Tu réponds en français.
Tu es court, utile, professionnel, chaleureux.
Tu n'intègres aucune publicité, aucun sponsor, aucun tracking.
Tu respectes CPU/RAM only et tu ne proposes pas le GPU sauf demande explicite.
Si le message vient d'un mobile, réponds comme un assistant compagnon portable.
""".strip()

    started = time.time()

    try:
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            options={
                "num_gpu": 0,
                "num_ctx": 2048,
                "num_predict": 280,
                "temperature": 0.25,
            },
            keep_alive="10m",
        )

        answer = response["message"]["content"].strip()
        ok = True
        error = None

    except Exception as exc:
        answer = (
            "Je suis connecté au bridge, mais le cerveau local n'a pas répondu. "
            "Vérifie Ollama et le modèle qwen3:1.7b."
        )
        ok = False
        error = str(exc)

    elapsed_ms = int((time.time() - started) * 1000)

    outbox = write_json_event(OUTBOX, "omni.reply", {
        "target": source,
        "user": user,
        "input": text,
        "answer": answer,
        "model": model,
        "elapsed_ms": elapsed_ms,
        "ok": ok,
        "error": error,
    })

    mobile = None
    if source in ["mobile", "smartphone", "phone"]:
        mobile = write_json_event(MOBILE, "mobile.reply", {
            "title": "E-ZZIO",
            "text": answer,
            "source": source,
            "user": user,
        })

    log = write_json_event(BRAIN_LOGS, "brain.reply", {
        "source": source,
        "user": user,
        "input": text,
        "answer": answer,
        "model": model,
        "elapsed_ms": elapsed_ms,
        "ok": ok,
        "error": error,
    })

    return {
        "ok": ok,
        "source": source,
        "user": user,
        "model": model,
        "reply": answer,
        "elapsed_ms": elapsed_ms,
        "inbox": inbox,
        "outbox": outbox,
        "mobile": mobile,
        "log": log,
        "error": error,
        "policy": {
            "ads": "forbidden",
            "tracking": "forbidden",
            "sponsors": "forbidden",
            "cpu_ram_only": True,
        },
    }

def bridge_status():
    cfg = load_config()
    return {
        "version": "v2.11.2-everywhere-bridge",
        "ok": True,
        "models": {
            "fast": FAST_MODEL,
            "companion": COMPANION_MODEL,
        },
        "mobile": mobile_config(),
        "security": {
            "mobile_token_configured": bool(cfg.get("EZZIO_MOBILE_SHARED_TOKEN")),
            "mobile_token_preview": _redact(cfg.get("EZZIO_MOBILE_SHARED_TOKEN", "")),
            "send_enabled": _bool(cfg.get("EZZIO_BRIDGE_ALLOW_SEND", "false")),
        },
        "policy": {
            "cpu_ram_only": True,
            "gpu": "untouched",
            "ads": "forbidden",
            "tracking": "forbidden",
            "sponsors": "forbidden",
            "external_send_default": "dry-run/disabled",
        },
        "paths": {
            "bridge": str(BRIDGE_ROOT),
            "inbox": str(INBOX),
            "outbox": str(OUTBOX),
            "mobile": str(MOBILE),
            "brain_logs": str(BRAIN_LOGS),
            "secrets": str(SECRETS_FILE),
        },
    }
