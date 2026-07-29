import os
import json
import time
import base64
from pathlib import Path

import ollama
from PIL import Image

PROJECT_ROOT = Path("G:/AI/E-zzio")
VISION_ROOT = PROJECT_ROOT / "forge" / "vision"
VISION_INBOX = VISION_ROOT / "inbox"
VISION_OUT = VISION_ROOT / "outputs"

MODEL_VISION = "qwen2.5vl:3b"
MODEL_FALLBACK_TEXT = "qwen3:1.7b"

CPU_ONLY_ENV = {
    "OLLAMA_NUM_GPU": "0",
    "CUDA_VISIBLE_DEVICES": "",
    "GGML_CUDA": "0",
    "CUDA_DEVICE_ORDER": "PCI_BUS_ID",
    "EZZIO_GPU_POLICY": "cpu_ram_only",
    "EZZIO_NUM_GPU": "0",
}

for key, value in CPU_ONLY_ENV.items():
    os.environ[key] = value

VISION_INBOX.mkdir(parents=True, exist_ok=True)
VISION_OUT.mkdir(parents=True, exist_ok=True)

def _safe_vision_path(path_text: str) -> Path:
    p = Path(path_text).resolve()

    allowed_roots = [
        VISION_INBOX.resolve(),
        VISION_OUT.resolve(),
        (PROJECT_ROOT / "forge").resolve(),
        (PROJECT_ROOT / "workspace").resolve(),
    ]

    if not any(str(p).startswith(str(root)) for root in allowed_roots):
        raise ValueError("Image refusée : hors forge/vision, forge ou workspace.")

    if not p.exists():
        raise FileNotFoundError(str(p))

    return p

def _image_info(path: Path):
    try:
        with Image.open(path) as img:
            return {
                "format": img.format,
                "width": img.width,
                "height": img.height,
                "mode": img.mode,
            }
    except Exception as exc:
        return {"error": str(exc)}

def save_upload_bytes(filename: str, content: bytes) -> Path:
    safe_name = Path(filename).name
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out = VISION_INBOX / f"{stamp}_{safe_name}"
    out.write_bytes(content)
    return out

def analyze_image_file(path_text: str, prompt: str = "", mode: str = "auto"):
    path = _safe_vision_path(path_text)
    info = _image_info(path)

    if "error" in info:
        return {
            "ok": False,
            "error": "Image invalide ou illisible.",
            "details": info,
        }

    user_prompt = prompt.strip() or (
        "Analyse cette image en français. "
        "Décris ce que tu vois, détecte les problèmes, lis les éléments visibles si possible, "
        "et propose une action utile. "
        "Si c'est une capture d'écran technique, cherche l'erreur, le fichier, le bouton, l'interface ou le symptôme."
    )

    started = time.time()

    try:
        response = ollama.chat(
            model=MODEL_VISION,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt,
                    "images": [str(path)],
                }
            ],
            options={
                "num_gpu": 0,
                "num_ctx": 3072,
                "num_predict": 420,
                "temperature": 0.20,
            },
            keep_alive="15m",
        )

        text = response["message"]["content"]
        ok = True
        error = None

    except Exception as exc:
        ok = False
        error = str(exc)
        text = (
            "Vision indisponible via qwen2.5vl:3b. "
            "Vérifie Ollama, le modèle, et le format image."
        )

    elapsed_ms = int((time.time() - started) * 1000)

    result = {
        "ok": ok,
        "model": MODEL_VISION,
        "cpu_ram_only": True,
        "path": str(path),
        "image": info,
        "mode": mode,
        "prompt": user_prompt,
        "analysis": text,
        "elapsed_ms": elapsed_ms,
        "error": error,
        "routing_hint": route_vision_result(text),
    }

    stamp = time.strftime("%Y%m%d_%H%M%S")
    out = VISION_OUT / f"vision_analysis_{stamp}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["saved_report"] = str(out)

    return result

def route_vision_result(text: str):
    lowered = str(text).lower()

    if any(x in lowered for x in ["traceback", "error", "erreur", "exception", "syntaxerror", "terminal", "powershell", "python"]):
        return {
            "next_organ": "mains",
            "reason": "capture technique ou erreur détectée",
            "next_action": "corriger/debugger",
        }

    if any(x in lowered for x in ["interface", "bouton", "layout", "ui", "écran", "ecran", "svelte"]):
        return {
            "next_organ": "yeux+mains",
            "reason": "interface ou UI détectée",
            "next_action": "diagnostic UI et correction frontend",
        }

    if any(x in lowered for x in ["image", "style", "composition", "visuel", "cinematic", "photo"]):
        return {
            "next_organ": "forge",
            "reason": "contenu visuel créatif",
            "next_action": "préparer prompt image/vidéo",
        }

    return {
        "next_organ": "presence",
        "reason": "analyse visuelle générale",
        "next_action": "répondre ou demander précision",
    }

def status():
    return {
        "version": "v2.9-vision-bridge",
        "model": MODEL_VISION,
        "fallback_text_model": MODEL_FALLBACK_TEXT,
        "cpu_ram_only": True,
        "paths": {
            "vision_root": str(VISION_ROOT),
            "inbox": str(VISION_INBOX),
            "outputs": str(VISION_OUT),
        },
        "capabilities": {
            "image_upload": True,
            "image_path_analysis": True,
            "screenshot_debug": True,
            "ui_analysis": True,
            "creative_prompt_help": True,
            "auto_routing_hint": True,
        },
    }
