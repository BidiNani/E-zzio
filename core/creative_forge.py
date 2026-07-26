import os
import json
import time
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import requests

PROJECT_ROOT = Path("G:/AI/E-zzio")
FORGE_ROOT = PROJECT_ROOT / "forge"
OUTPUT_ROOT = FORGE_ROOT / "outputs"
WORKFLOWS_ROOT = FORGE_ROOT / "workflows"
MOBILE_ROOT = FORGE_ROOT / "mobile"
EXTERNAL_ROOT = Path("G:/AI/external")
COMFY_ROOT = EXTERNAL_ROOT / "ComfyUI"
COMFY_URL = "http://127.0.0.1:8188"

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

OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
WORKFLOWS_ROOT.mkdir(parents=True, exist_ok=True)
MOBILE_ROOT.mkdir(parents=True, exist_ok=True)

def _safe_output_path(relative_path: str) -> Path:
    candidate = (OUTPUT_ROOT / str(relative_path)).resolve()
    if not str(candidate).startswith(str(OUTPUT_ROOT.resolve())):
        raise ValueError("Chemin refusé : hors forge/outputs.")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    return candidate

def _cpu_env():
    env = os.environ.copy()
    env.update(CPU_ONLY_ENV)
    return env

def comfy_health():
    try:
        r = requests.get(f"{COMFY_URL}/system_stats", timeout=3)
        data = r.json()
        return {
            "ok": r.status_code < 400,
            "status_code": r.status_code,
            "data": data,
            "cpu_ram_only_policy": True,
            "warning": "Si ComfyUI affiche un device GPU, relance-le avec scripts/start_comfyui_cpu_safe.ps1.",
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "cpu_ram_only_policy": True,
        }

def status():
    return {
        "version": "v2.9-indispensable-core",
        "policy": {
            "global": "CPU/RAM only",
            "ollama_gpu": "disabled",
            "comfyui_gpu": "disabled by --cpu script",
            "ffmpeg": "CPU encoding only",
            "apk_build": "CPU build tools only",
            "dangerous_filesystem": "sandboxed_outputs_only",
        },
        "paths": {
            "forge_root": str(FORGE_ROOT),
            "outputs": str(OUTPUT_ROOT),
            "workflows": str(WORKFLOWS_ROOT),
            "mobile": str(MOBILE_ROOT),
            "comfy_root": str(COMFY_ROOT),
        },
        "environment_lock": CPU_ONLY_ENV,
        "availability": {
            "comfyui_installed": COMFY_ROOT.exists(),
            "comfyui_online": comfy_health()["ok"],
            "ffmpeg": bool(shutil.which("ffmpeg")),
            "node": bool(shutil.which("node")),
            "npm": bool(shutil.which("npm")),
            "java": bool(shutil.which("java")),
            "android_home": bool(os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")),
        },
        "practical_note": {
            "image_cpu": "possible mais lent",
            "video_cpu": "préférer keyframes + ffmpeg",
            "apk_cpu": "OK avec Node + Android SDK",
            "vision_cpu": "qwen2.5vl:3b via Ollama CPU-only",
        },
    }

def save_prompt_file(kind: str, prompt: str, negative: str = "", meta: Optional[dict] = None):
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = _safe_output_path(f"{kind}/prompt_{stamp}.json")
    payload = {
        "kind": kind,
        "prompt": prompt,
        "negative": negative,
        "created_at": stamp,
        "meta": meta or {},
        "cpu_ram_only": True,
        "note": "Prompt préparé par E-ZZIO. Génération réelle via pipeline CPU-only ou ComfyUI --cpu.",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "path": str(path), "payload": payload}

def make_image_prompt(prompt: str, style: str = "cinematic", negative: str = ""):
    enriched = (
        f"{prompt}\n"
        f"Style: {style}. CPU-friendly generation, small resolution first, coherent composition, clean lighting."
    )
    neg = negative or "low quality, blurry, distorted hands, text artifacts, watermark"
    return save_prompt_file("image", enriched, neg, {
        "style": style,
        "recommended_cpu_settings": {
            "resolution": "512x512 first",
            "steps": "12-20",
            "batch": 1,
            "note": "Monter la qualité seulement si le temps CPU reste acceptable."
        }
    })

def make_video_plan(prompt: str, duration_sec: int = 4, fps: int = 8, style: str = "cinematic"):
    duration_sec = max(1, min(int(duration_sec), 12))
    fps = max(4, min(int(fps), 12))
    frames = duration_sec * fps

    plan = {
        "prompt": prompt,
        "style": style,
        "duration_sec": duration_sec,
        "fps": fps,
        "estimated_frames": frames,
        "cpu_ram_only": True,
        "recommended_cpu_limits": {
            "max_duration_sec": 12,
            "max_fps": 12,
            "recommended_resolution": "512x512 or lower",
            "preferred_method": "generate keyframes, then FFmpeg assembly",
        },
        "pipeline": [
            "préparer prompt et storyboard",
            "générer peu de keyframes en CPU",
            "assembler les frames avec FFmpeg CPU",
            "exporter MP4 dans forge/outputs/video",
        ],
        "warning": "La vidéo IA complète en CPU pur peut être extrêmement lente. E-ZZIO privilégie plans courts, keyframes et assemblage.",
    }

    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = _safe_output_path(f"video/video_plan_{stamp}.json")
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "path": str(path), "plan": plan}

def ffmpeg_make_video_from_folder(folder: str, fps: int = 8, output_name: str = "ezzio_video_cpu.mp4"):
    if not shutil.which("ffmpeg"):
        return {"ok": False, "error": "ffmpeg introuvable dans le PATH."}

    source = Path(folder).resolve()
    if not source.exists():
        return {"ok": False, "error": f"Dossier introuvable: {source}"}

    out = _safe_output_path(f"video/{output_name}")
    fps = max(4, min(int(fps), 30))

    cmd = [
        "ffmpeg",
        "-y",
        "-framerate", str(fps),
        "-pattern_type", "glob",
        "-i", str(source / "*.png"),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        str(out),
    ]

    started = time.time()
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
        env=_cpu_env(),
    )

    return {
        "ok": proc.returncode == 0,
        "cpu_ram_only": True,
        "output": str(out),
        "elapsed_sec": round(time.time() - started, 2),
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
        "cmd": cmd,
    }

def apk_status():
    ui_root = PROJECT_ROOT / "ezzio-ui"
    package_json = ui_root / "package.json"

    return {
        "cpu_ram_only": True,
        "ui_root": str(ui_root),
        "package_json": package_json.exists(),
        "node": bool(shutil.which("node")),
        "npm": bool(shutil.which("npm")),
        "java": bool(shutil.which("java")),
        "android_home": os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT"),
        "expected_output": str(ui_root / "android" / "app" / "build" / "outputs" / "apk"),
        "note": "Build APK = CPU classique. L'APK est une interface vers l'API E-ZZIO.",
    }

def write_mobile_manifest(app_name: str = "E-ZZIO", app_id: str = "com.ezzio.local"):
    manifest = {
        "app_name": app_name,
        "app_id": app_id,
        "frontend": "G:/AI/E-zzio/ezzio-ui",
        "backend": "http://127.0.0.1:8000",
        "cpu_ram_only": True,
        "strategy": "SvelteKit static adapter + Capacitor Android",
        "warning": "L'APK local ne contient pas Ollama + modèles. Il sert d'interface mobile vers l'API E-ZZIO.",
    }
    path = MOBILE_ROOT / "mobile_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "path": str(path), "manifest": manifest}
