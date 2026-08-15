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
LOCAL_BASE = "http://127.0.0.1:8001"

PROJECT_LEXICON = """
Lexique E-ZZIO :
- bridge = pont logiciel E-ZZIO entre API locale, PC, smartphone LAN, Discord/Messenger officiels. Jamais pont routier.
- everywhere / partout = ambition d'accessibilité multi-support, pas une preuve que tout est déjà connecté.
- smartphone = actuellement bridge LAN/API prêt ; vraie application APK/mobile pas encore finalisée sauf preuve contraire.
- Discord = module prêt côté API ; envoi réel seulement si webhook/token configuré et EZZIO_BRIDGE_ALLOW_SEND=true.
- Messenger = module prêt côté API ; envoi réel seulement avec Meta Page token + PSID + autorisation.
- vocal = pas encore intégré sauf module futur explicite.
- no ads = aucune pub, aucun tracking, aucun sponsor.
- CPU/RAM only = GPU/VRAM non utilisé.
""".strip()

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
        "META_DEFAULT_RECIPIENT_PSID",
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

def integration_truth():
    cfg = load_config()
    send_enabled = _bool(cfg.get("EZZIO_BRIDGE_ALLOW_SEND", "false"))

    return {
        "ok": True,
        "truth_policy": "E-ZZIO doit distinguer prêt, configuré, connecté et actif.",
        "pc": {
            "state": "active",
            "detail": "API locale E-ZZIO active sur le PC.",
        },
        "smartphone": {
            "state": "bridge_ready",
            "detail": "Bridge LAN/API prêt. Accès possible via navigateur ou future app si start_ezzio_lan.ps1 est lancé.",
            "not_yet": ["application APK finale non confirmée", "commandes vocales non intégrées"],
        },
        "discord": {
            "state": "ready_not_configured" if not (cfg.get("DISCORD_WEBHOOK_URL") or cfg.get("DISCORD_BOT_TOKEN")) else "configured",
            "webhook_configured": bool(cfg.get("DISCORD_WEBHOOK_URL")),
            "bot_configured": bool(cfg.get("DISCORD_BOT_TOKEN")),
            "send_enabled": send_enabled,
            "detail": "Connecteur officiel prêt. Envoi réel verrouillé par EZZIO_BRIDGE_ALLOW_SEND.",
        },
        "messenger": {
            "state": "ready_not_configured" if not cfg.get("META_PAGE_ACCESS_TOKEN") else "configured",
            "page_token_configured": bool(cfg.get("META_PAGE_ACCESS_TOKEN")),
            "recipient_configured": bool(cfg.get("META_DEFAULT_RECIPIENT_PSID")),
            "send_enabled": send_enabled,
            "detail": "Connecteur Meta Page prêt côté API. Nécessite token Page + PSID.",
        },
        "ads": {
            "state": "forbidden",
            "detail": "Aucune pub, aucun tracking, aucun sponsor.",
        },
        "gpu": {
            "state": "untouched",
            "detail": "CPU/RAM only. GTX réservée.",
        },
    }

def mobile_config():
    cfg = load_config()
    ips = get_lan_ips()
    token = cfg.get("EZZIO_MOBILE_SHARED_TOKEN", "")

    urls = []
    for ip in ips:
        urls.append({
            "host": ip,
            "base_url": f"http://{ip}:8001",
            "status": f"http://{ip}:8001/status",
            "router_status": f"http://{ip}:8001/router-status",
            "mobile_pull": f"http://{ip}:8001/omni/mobile/pull",
            "mobile_inbox": f"http://{ip}:8001/omni/mobile/inbox",
            "omni_reply": f"http://{ip}:8001/omni-bridge/reply",
            "mobile_reply": f"http://{ip}:8001/omni-bridge/mobile/reply",
            "commands": f"http://{ip}:8001/omni-bridge/commands",
            "truth": f"http://{ip}:8001/omni-bridge/truth",
        })

    return {
        "ok": True,
        "name": "E-ZZIO Mobile Bridge",
        "status": "bridge_ready_not_full_app",
        "policy": {
            "local_wifi_only": True,
            "token_required_for_mobile_reply": True,
            "ads": "forbidden",
            "tracking": "forbidden",
            "gpu": "untouched",
        },
        "urls": urls,
        "token_preview": _redact(token),
        "headers": {"X-EZZIO-Mobile-Token": "<token dans secrets/omnipresence.env>"},
        "commands": available_commands()["commands"],
        "truth": integration_truth()["smartphone"],
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

def local_status_payload():
    return {
        "ok": True,
        "version": "v2.11.5-no-self-deadlock",
        "project_root": str(PROJECT_ROOT),
        "policy": {
            "cpu_ram_only": True,
            "ollama_num_gpu": os.environ.get("OLLAMA_NUM_GPU"),
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "ezzio_gpu_policy": os.environ.get("EZZIO_GPU_POLICY"),
            "no_ads": os.environ.get("EZZIO_NO_ADS"),
            "no_tracking": os.environ.get("EZZIO_NO_TRACKING"),
            "no_sponsors": os.environ.get("EZZIO_NO_SPONSORS"),
        },
    }

def local_router_status_payload():
    try:
        import sys
        web_server = sys.modules.get("web_server")
        report = getattr(web_server, "router_load_report", None)

        if report:
            return {
                "ok": True,
                "source": "in_memory",
                "loaded_count": len(report.get("loaded", [])),
                "failed_count": len(report.get("failed", {})),
                "loaded": report.get("loaded", []),
                "failed": report.get("failed", {}),
            }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    return {
        "ok": False,
        "error": "router_load_report indisponible en mémoire",
    }

def no_ads_policy_payload():
    return {
        "ok": True,
        "policy": "E-ZZIO ne doit intégrer aucune publicité, aucun tracking publicitaire, aucun sponsor, aucune recommandation payée.",
        "allowed": [
            "connecteurs officiels configurés par Enrik",
            "webhooks explicites",
            "API publiques utiles",
            "logs locaux",
            "bridge mobile local",
        ],
        "forbidden": [
            "ads",
            "sponsored content",
            "tracking pixels",
            "profilage publicitaire",
            "vente de données",
            "modules de pub dans UI/API/mobile",
        ],
    }

def local_forge_status_payload():
    try:
        from core.creative_forge import status
        return {"ok": True, "source": "core.creative_forge.status", "data": status()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

def local_vision_status_payload():
    try:
        from core.vision_bridge import status
        return {"ok": True, "source": "core.vision_bridge.status", "data": status()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

def _get_json(path: str, timeout: int = 8):
    """
    v2.11.5 : évite les appels HTTP internes à 127.0.0.1:8001 depuis une requête API,
    car un seul worker peut provoquer un auto-deadlock/timeout.
    """
    if path == "/status":
        return local_status_payload()

    if path == "/router-status":
        return local_router_status_payload()

    if path == "/no-ads-policy":
        return no_ads_policy_payload()

    if path == "/forge/status":
        return local_forge_status_payload()

    if path == "/vision/status":
        return local_vision_status_payload()

    return {
        "ok": False,
        "error": f"Commande interne non mappée sans HTTP : {path}",
    }

def available_commands():
    return {
        "ok": True,
        "commands": [
            {"command": "/help", "description": "Liste des commandes."},
            {"command": "/whoami", "description": "Identité E-ZZIO."},
            {"command": "/truth", "description": "Ce qui est actif, prêt, ou pas encore configuré."},
            {"command": "/everywhere", "description": "État PC/smartphone/Discord/Messenger."},
            {"command": "/status", "description": "État API."},
            {"command": "/routers", "description": "Routers chargés/échoués."},
            {"command": "/forge", "description": "État Forge/ComfyUI/FFmpeg/APK."},
            {"command": "/vision", "description": "État Vision/Yeux."},
            {"command": "/mobile", "description": "Config smartphone LAN."},
            {"command": "/discord", "description": "État connecteur Discord."},
            {"command": "/messenger", "description": "État connecteur Messenger."},
            {"command": "/noads", "description": "Politique zéro pub/tracking/sponsor."},
        ],
    }

def _compact_json(data: Dict[str, Any]):
    return json.dumps(data, ensure_ascii=False, indent=2)

def handle_command(text: str):
    command = str(text or "").strip().split()[0].lower()
    truth = integration_truth()

    if command in ["/help", "help", "commandes", "commands"]:
        lines = ["Commandes E-ZZIO :"]
        for item in available_commands()["commands"]:
            lines.append(f"- {item['command']} : {item['description']}")
        return {"handled": True, "reply": "\n".join(lines)}

    if command == "/whoami":
        return {
            "handled": True,
            "reply": (
                "Je suis E-ZZIO, l'ami IA local d'Enrik : API PC, bridge smartphone LAN, "
                "connecteurs Discord/Messenger officiels, Vision, Forge, mémoire et autonomie. "
                "CPU/RAM only. Zéro pub, zéro tracking, zéro sponsor."
            ),
        }

    if command in ["/truth", "/everywhere"]:
        return {"handled": True, "reply": _compact_json(truth)}

    if command == "/discord":
        return {"handled": True, "reply": _compact_json(truth["discord"])}

    if command == "/messenger":
        return {"handled": True, "reply": _compact_json(truth["messenger"])}

    if command == "/status":
        return {"handled": True, "reply": _compact_json(_get_json("/status"))}

    if command == "/routers":
        return {"handled": True, "reply": _compact_json(_get_json("/router-status"))}

    if command == "/forge":
        return {"handled": True, "reply": _compact_json(_get_json("/forge/status"))}

    if command == "/vision":
        return {"handled": True, "reply": _compact_json(_get_json("/vision/status"))}

    if command == "/mobile":
        return {"handled": True, "reply": _compact_json(mobile_config())}

    if command == "/noads":
        return {"handled": True, "reply": _compact_json(_get_json("/no-ads-policy"))}

    return {"handled": False}

def sanitize_reply(answer: str):
    answer = str(answer or "").strip()

    forbidden_claims = [
        "Je suis déjà connecté à votre smartphone",
        "je suis déjà connecté à votre smartphone",
        "commandes vocales",
        "mode omni est activé, donc je suis partout",
        "je suis partout",
        "application",
    ]

    lowered = answer.lower()
    risky = False

    if "commandes vocales" in lowered:
        risky = True

    if "déjà connecté" in lowered and "smartphone" in lowered:
        risky = True

    if "application" in lowered and "smartphone" in lowered:
        risky = True

    if risky:
        answer = (
            "Le bridge E-ZZIO est prêt côté logiciel : API locale, accès LAN smartphone possible, "
            "Discord/Messenger préparés via connecteurs officiels. "
            "Mais je ne dois pas prétendre qu'une vraie app smartphone ou des commandes vocales sont déjà actives tant qu'elles ne sont pas installées/configurées."
        )

    return answer

def build_system_prompt(source: str, mode: str):
    tone = "Réponds court, concret, avec chaleur discrète."
    if source in ["mobile", "smartphone", "phone"]:
        tone = "Réponds comme un compagnon mobile : clair, rapide, honnête."
    if mode == "companion":
        tone = "Réponds comme un ami IA local : chaleureux, mais pas bavard."

    return f"""
Tu es E-ZZIO, l'ami IA local d'Enrik.

Vérité obligatoire :
- Ne dis jamais que tu es déjà sur smartphone si seule l'API LAN est prête.
- Ne dis jamais qu'une application mobile existe si elle n'a pas été construite/installée.
- Ne dis jamais que les commandes vocales existent si aucun module vocal n'est installé.
- Ne dis jamais que Discord/Messenger sont actifs si les tokens ne sont pas configurés et l'envoi autorisé.
- Utilise les mots : prêt, configuré, actif, pas encore fait.
- Quand Enrik dit "bridge", c'est le bridge logiciel E-ZZIO, pas un pont routier.

Identité :
- Projet local : G:/AI/E-zzio.
- Objectif : rendre E-ZZIO accessible sur PC, smartphone, Discord/Messenger, Vision, Forge, mémoire, autonomie.
- CPU/RAM only. GPU/VRAM non utilisé.
- Zéro pub, zéro sponsor, zéro tracking.

Style :
- Français.
- {tone}
- Si la demande est ambiguë, donne l'état réel.

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
            "truth": integration_truth(),
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
                "num_predict": 220,
                "temperature": 0.12,
            },
            keep_alive="10m",
        )

        answer = response["message"]["content"].strip()
        answer = sanitize_reply(answer)
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
        "truth": integration_truth(),
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
        "version": "v2.11.4-truth-guard-omni-commands",
        "ok": True,
        "identity": {
            "name": "E-ZZIO",
            "meaning": "ami IA local et organisme logiciel d'Enrik",
            "bridge_definition": "pont logiciel entre API PC, smartphone LAN, Discord/Messenger officiels",
        },
        "models": {
            "fast": FAST_MODEL,
            "companion": COMPANION_MODEL,
        },
        "commands": available_commands()["commands"],
        "truth": integration_truth(),
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



