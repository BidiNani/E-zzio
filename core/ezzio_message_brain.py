from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

from core.ezzio_truth_guard import (
    REAL_PC_PROFILE_TEXT,
    correction_ack,
    is_user_correction,
    sanitize_reply,
    system_prompt,
)

PROJECT_ROOT = Path("G:/AI/E-zzio")
UPLOAD_DIR = PROJECT_ROOT / "forge" / "vision" / "inbox"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
CHAT_MODEL = os.environ.get("EZZIO_CHAT_MODEL", "hermes3:8b")
FAST_MODEL = os.environ.get("EZZIO_FAST_MODEL", "llama3.2:3b")

for key, value in {
    "OLLAMA_NUM_GPU": "0",
    "CUDA_VISIBLE_DEVICES": "",
    "GGML_CUDA": "0",
    "CUDA_DEVICE_ORDER": "PCI_BUS_ID",
    "EZZIO_GPU_POLICY": "cpu_ram_only",
    "EZZIO_NUM_GPU": "0",
    "EZZIO_NO_ADS": "true",
    "EZZIO_NO_TRACKING": "true",
    "EZZIO_NO_SPONSORS": "true",
}.items():
    os.environ[key] = value

def intent_of(text: str, has_image: bool) -> str:
    t = (text or "").lower()

    if has_image:
        return "vision"

    if any(w in t for w in [
        "cherche", "recherche", "documente", "source", "sources",
        "wikipedia", "infos sur", "trouve des infos"
    ]):
        return "research"

    if any(w in t for w in [
        "audit", "maintenance", "système", "systeme", "actions en attente",
        "confirme", "annule", "état rapide", "etat rapide", "configuration",
        "combien de ram", "gpu", "cpu"
    ]):
        return "system"

    return "chat"

def ollama(prompt: str, model: str | None = None, timeout: int = 240) -> Dict[str, Any]:
    payload = {
        "model": model or CHAT_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_ctx": 4096,
            "num_predict": 700,
            "num_gpu": 0,
        },
    }

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8", errors="replace"))

    return {
        "ok": True,
        "model": payload["model"],
        "reply": (data.get("response") or "").strip(),
        "raw": data,
    }

def web_research(query: str) -> Dict[str, Any]:
    q = (query or "").strip()
    if not q:
        return {"ok": False, "reply": "Recherche vide.", "sources": []}

    url = "https://fr.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "opensearch",
        "search": q,
        "limit": "5",
        "namespace": "0",
        "format": "json",
    })

    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))

        titles = data[1] if len(data) > 1 else []
        descriptions = data[2] if len(data) > 2 else []
        links = data[3] if len(data) > 3 else []

        sources: List[Dict[str, str]] = []
        for title, desc, link in zip(titles, descriptions, links):
            sources.append({"title": title, "summary": desc, "url": link})

        if not sources:
            return {
                "ok": False,
                "reply": "Je n'ai trouvé aucune source Wikipédia exploitable pour cette recherche.",
                "sources": [],
                "provider": "wikipedia_opensearch",
            }

        source_text = "\n".join([f"- {s['title']}: {s['summary']} ({s['url']})" for s in sources])
        synth_prompt = f"""
{system_prompt("research")}

Fais une synthèse courte, utile et honnête à partir de ces sources.
Ne prétends pas avoir cherché ailleurs que dans les sources fournies.

Question :
{q}

Sources :
{source_text}
""".strip()

        synth = ollama(synth_prompt, FAST_MODEL, timeout=180)

        return {
            "ok": True,
            "reply": synth["reply"],
            "sources": sources,
            "provider": "wikipedia_opensearch",
            "model": synth["model"],
        }

    except Exception as exc:
        fallback = ollama(
            f"""{system_prompt("research")}

Réponds prudemment à cette demande de recherche, sans inventer de sources.
Dis clairement que la recherche web directe est indisponible.

Demande :
{q}
""".strip(),
            FAST_MODEL,
            timeout=180,
        )

        return {
            "ok": True,
            "reply": fallback["reply"] + "\n\nNote : recherche web directe indisponible, réponse locale prudente.",
            "sources": [],
            "provider": "local_fallback",
            "error": str(exc),
            "model": fallback["model"],
        }

def chat_answer(text: str, intent: str) -> Dict[str, Any]:
    if is_user_correction(text):
        return {
            "ok": True,
            "model": "truth_guard",
            "reply": correction_ack(text),
            "raw": {"deterministic": True, "intent": intent},
        }

    t = (text or "").lower()
    if "état rapide" in t or "etat rapide" in t or "combien de ram" in t or "configuration" in t:
        return {
            "ok": True,
            "model": "truth_guard",
            "reply": (
                "État rapide E-ZZIO : système local opérationnel.\n\n"
                f"{REAL_PC_PROFILE_TEXT}\n\n"
                "Je ne dois pas inventer de matériel. Les actions E-ZZIO restent en CPU/RAM only, GPU untouched."
            ),
            "raw": {"deterministic": True, "intent": intent},
        }

    prompt = f"""
{system_prompt(intent)}

Message utilisateur :
{text}
""".strip()

    model = FAST_MODEL if intent == "system" else CHAT_MODEL
    return ollama(prompt, model, timeout=240)

def vision_answer(path: str, text: str) -> Dict[str, Any]:
    try:
        from core.smart_vision import analyze_path

        prompt = text or (
            "Analyse cette image précisément. Si c'est un logo, une icône ou une illustration, "
            "décris les formes, couleurs, contours, style et ce que cela évoque. "
            "Ne propose jamais PowerShell sauf capture technique."
        )

        result = analyze_path(path, prompt)

        if "reply" in result:
            result["reply"] = sanitize_reply(result["reply"], text)

        return result

    except Exception as exc:
        return {
            "ok": False,
            "reply": f"Erreur vision : {exc}",
            "error": str(exc),
        }

def save_upload(filename: str, content: bytes) -> Path:
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in (filename or "image.png"))
    target = UPLOAD_DIR / f"chat_{time.strftime('%Y%m%d_%H%M%S')}_{safe}"
    target.write_bytes(content)
    return target

def handle_message(text: str = "", image_path: str | None = None) -> Dict[str, Any]:
    started = time.time()
    intent = intent_of(text, bool(image_path))

    if intent == "vision" and image_path:
        result = vision_answer(image_path, text)
    elif intent == "research":
        result = web_research(text)
    else:
        result = chat_answer(text, intent)

    raw_reply = (
        result.get("reply")
        or result.get("analysis")
        or result.get("message")
        or "Réponse vide."
    )

    reply = sanitize_reply(raw_reply, text)

    return {
        "ok": result.get("ok", True),
        "version": "v2.31.1b-safe-brain-restore",
        "intent": intent,
        "reply": reply,
        "result": result,
        "elapsed_ms": int((time.time() - started) * 1000),
        "policy": {
            "cpu_ram_only": True,
            "gpu": "untouched",
            "no_ads": True,
            "truth_guard": True,
        },
    }
