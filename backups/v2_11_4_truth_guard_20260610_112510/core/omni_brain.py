import os
import json
import time
import uuid
import socket
from pathlib import Path
from typing import Dict, Any

import requests
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

LOCAL_BASE = "http://127.0.0.1:8000"

PROJECT_LEXICON = """
Lexique E-ZZIO obligatoire :
- bridge = pont logiciel E-ZZIO entre PC, smartphone, Discord, Messenger et API locale. Jamais un pont routier.
- omni / omnipresence = module qui permet à E-ZZIO d'être partout.
- forge = module image/vidéo/ComfyUI/FFmpeg/APK.
- vision / yeux = analyse d'image qwen2.5vl:3b.
- mains = correction technique, scripts, PowerShell.
- présence = compagnon local.
- no ads = aucune pub, aucun sponsor, aucun tracking.
- CPU/RAM only = GPU/VRAM non utilisé, GTX gardée libre.
""".strip()

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
            "router_status": f"http://{ip}:8000/router-status",
            "mobile_pull": f"http://{ip}:8000/omni/mobile/pull",
            "mobile_inbox": f"http://{ip}:8000/omni/mobile/inbox",
            "omni_reply": f"http://{ip}:8000/omni-bridge/reply",
            "mobile_reply": f"http://{ip}:8000/omni-bridge/mobile/reply",
            "commands": f"http://{ip}:8000/omni-bridge/commands",
        })

    return {
        "ok": True,
        "name": "E-ZZIO Mobile Bridge",
        "policy": {
            "local_wifi_only": True,
            "token_required_for_mobile_reply": True,
            "ads": "forbidden",
            "tracking": "forbidden",
            "gpu": "untouched",
        },
        "urls": urls,
        "token_preview": _redact(token),
        "headers": {
            "X-EZZIO-Mobile-Token": "<token dans secrets/omnipresence.env>"
        },
        "commands": available_commands()["commands"],
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

def _get_json(path: str, timeout: int = 8):
    try:
        r = requests.get(f"{LOCAL_BASE}{path}", timeout=timeout)
        return {"ok": r.status_code < 400, "status_code": r.status_code, "data": r.json()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

def available_commands():
    return {
        "ok": True,
        "commands": [
            {"command": "/help", "description": "Liste les commandes."},
            {"command": "/status", "description": "État API E-ZZIO."},
            {"command": "/routers", "description": "Liste routers chargés/échoués."},
            {"command": "/forge", "description": "État Forge/ComfyUI/FFmpeg/APK."},
            {"command": "/vision", "description": "État Vision/Yeux."},
            {"command": "/mobile", "description": "Config smartphone LAN."},
            {"command": "/noads", "description": "Politique zéro pub/tracking/sponsor."},
            {"command": "/whoami", "description": "Identité E-ZZIO."},
        ],
    }

def handle_command(text: str):
    command = str(text or "").strip().split()[0].lower()

    if command in ["/help", "help"]:
        return {"handled": True, "reply": json.dumps(available_commands(), ensure_ascii=False, indent=2)}

    if command == "/status":
        data = _get_json("/status")
        return {"handled": True, "reply": json.dumps(data, ensure_ascii=False, indent=2)}

    if command == "/routers":
        data = _get_json("/router-status")
        return {"handled": True, "reply": json.dumps(data, ensure_ascii=False, indent=2)}

    if command == "/forge":
        data = _get_json("/forge/status")
        return {"handled": True, "reply": json.dumps(data, ensure_ascii=False, indent=2)}

    if command == "/vision":
        data = _get_json("/vision/status")
        return {"handled": True, "reply": json.dumps(data, ensure_ascii=False, indent=2)}

    if command == "/mobile":
        return {"handled": True, "reply": json.dumps(mobile_config(), ensure_ascii=False, indent=2)}

    if command == "/noads":
        data = _get_json("/no-ads-policy")
        return {"handled": True, "reply": json.dumps(data, ensure_ascii=False, indent=2)}

    if command == "/whoami":
        return {
            "handled": True,
            "reply": (
                "Je suis E-ZZIO, l'ami IA local d'Enrik : PC, smartphone, Discord/Messenger via connecteurs officiels, "
                "Vision, Forge, mémoire, autonomie. CPU/RAM only. Zéro pub, zéro tracking, zéro sponsor."
            ),
        }

    return {"handled": False}

def build_system_prompt(source: str, mode: str):
    tone = "Réponds court, concret, avec une chaleur discrète."
    if source in ["mobile", "smartphone", "phone"]:
        tone = "Réponds comme un compagnon mobile : très clair, rapide, pratique."
    if mode == "companion":
        tone = "Réponds comme un ami IA local : chaleureux, mais pas bavard."

    return f"""
Tu es E-ZZIO, l'ami IA local d'Enrik.

Identité :
- Tu n'es pas un assistant générique.
- Tu fais partie du projet local G:/AI/E-zzio.
- Tu aides Enrik à faire vivre un organisme logiciel : PC, smartphone, Discord, Messenger, Vision, Forge, mémoire, autonomie.
- Quand Enrik dit "bridge", il parle du bridge logiciel E-ZZIO, jamais d'un pont routier.
- Quand Enrik dit "partout", il parle de rendre E-ZZIO disponible sur PC, smartphone et connecteurs officiels.

Règles :
- Français.
- {tone}
- Zéro publicité, zéro sponsor, zéro tracking.
- CPU/RAM only : ne propose pas GPU/VRAM sauf demande explicite.
- Ne prétends pas envoyer réellement sur Discord/Messenger si le mode dry-run est actif.
- Si une demande concerne un script, réponds PowerShell propre.
- Si tu ne sais pas, demande une sortie/log précis.

{PROJECT_LEXICON}
""".strip()

def local_brain_reply(text: str, source: str = "mobile", user: str = "enrik", mode: str = "fast"):
    text = str(text or "").strip()

    if not text:
        return {"ok": False, "error": "Message vide."}

    inbox = write_json_event(INBOX, "omni.inbox", {
        "source": source,
        "user": user,
        "text": text,
        "mode": mode,
    })

    command = handle_command(text)
    if command.get("handled"):
        answer = command["reply"]
        outbox = write_json_event(OUTBOX, "omni.command.reply", {
            "target": source,
            "user": user,
            "input": text,
            "answer": answer,
            "model": "command-router",
            "ok": True,
        })

        mobile = None
        if source in ["mobile", "smartphone", "phone"]:
            mobile = write_json_event(MOBILE, "mobile.command.reply", {
                "title": "E-ZZIO",
                "text": answer,
                "source": source,
                "user": user,
            })

        return {
            "ok": True,
            "source": source,
            "user": user,
            "model": "command-router",
            "reply": answer,
            "elapsed_ms": 0,
            "inbox": inbox,
            "outbox": outbox,
            "mobile": mobile,
            "error": None,
            "policy": {"ads": "forbidden", "tracking": "forbidden", "sponsors": "forbidden", "cpu_ram_only": True},
        }

    model = FAST_MODEL if mode != "companion" else COMPANION_MODEL
    system = build_system_prompt(source=source, mode=mode)
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
                "num_predict": 260,
                "temperature": 0.18,
            },
            keep_alive="10m",
        )

        answer = response["message"]["content"].strip()
        ok = True
        error = None

    except Exception as exc:
        answer = (
            "Je suis connecté au bridge E-ZZIO, mais le cerveau local n'a pas répondu. "
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
        "version": "v2.11.3-omni-identity-command-center",
        "ok": True,
        "identity": {
            "name": "E-ZZIO",
            "meaning": "ami IA local et organisme logiciel d'Enrik",
            "bridge_definition": "pont logiciel entre PC, smartphone, Discord, Messenger et API locale",
        },
        "models": {
            "fast": FAST_MODEL,
            "companion": COMPANION_MODEL,
        },
        "commands": available_commands()["commands"],
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
