import os
import subprocess
import time
from pathlib import Path

import httpx

PROJECT_ROOT = Path("G:/AI/E-zzio")
COMFY_ROOT = Path("G:/AI/external/ComfyUI")
COMFY_PY = COMFY_ROOT / ".venv" / "Scripts" / "python.exe"
COMFY_URL = "http://127.0.0.1:8188"

CHECKPOINTS = COMFY_ROOT / "models" / "checkpoints"
VAE = COMFY_ROOT / "models" / "vae"
LORAS = COMFY_ROOT / "models" / "loras"
OUTPUT = COMFY_ROOT / "output"
WORKFLOWS = PROJECT_ROOT / "forge" / "workflows"
LOGS = PROJECT_ROOT / "logs" / "comfy_autostart"

DEFAULT_CKPT = "DreamShaper_8_pruned.safetensors"

CPU_ONLY_ENV = {
    "OLLAMA_NUM_GPU": "0",
    "CUDA_VISIBLE_DEVICES": "",
    "GGML_CUDA": "0",
    "CUDA_DEVICE_ORDER": "PCI_BUS_ID",
    "EZZIO_GPU_POLICY": "cpu_ram_only",
    "EZZIO_NUM_GPU": "0",
    "PYTORCH_ENABLE_MPS_FALLBACK": "0",
}


def _cpu_env():
    env = os.environ.copy()
    env.update(CPU_ONLY_ENV)
    return env


def comfy_health():
    try:
        r = httpx.get(f"{COMFY_URL}/system_stats", timeout=5)
        return {
            "ok": r.status_code < 400,
            "status_code": r.status_code,
            "data": r.json(),
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


def ensure_comfy_online(timeout_sec: int = 180):
    health = comfy_health()
    if health.get("ok"):
        return {
            "ok": True,
            "started": False,
            "health": health,
        }

    if not COMFY_PY.exists():
        return {
            "ok": False,
            "started": False,
            "error": f"ComfyUI Python introuvable : {COMFY_PY}",
            "health": health,
        }

    main_py = COMFY_ROOT / "main.py"
    if not main_py.exists():
        return {
            "ok": False,
            "started": False,
            "error": f"ComfyUI main.py introuvable : {main_py}",
            "health": health,
        }

    LOGS.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    stdout = LOGS / f"comfy_{stamp}.stdout.log"
    stderr = LOGS / f"comfy_{stamp}.stderr.log"

    with stdout.open("wb") as out, stderr.open("wb") as err:
        proc = subprocess.Popen(
            [str(COMFY_PY), "main.py", "--listen", "127.0.0.1", "--port", "8188", "--cpu"],
            cwd=str(COMFY_ROOT),
            stdout=out,
            stderr=err,
            env=_cpu_env(),
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

    deadline = time.time() + timeout_sec

    while time.time() < deadline:
        health = comfy_health()
        if health.get("ok"):
            return {
                "ok": True,
                "started": True,
                "pid": proc.pid,
                "stdout": str(stdout),
                "stderr": str(stderr),
                "health": health,
            }
        time.sleep(2)

    return {
        "ok": False,
        "started": True,
        "pid": proc.pid,
        "stdout": str(stdout),
        "stderr": str(stderr),
        "error": "ComfyUI n'a pas répondu dans le délai.",
        "health": comfy_health(),
    }


def _model_files(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    out = []
    for p in path.iterdir():
        if p.is_file() and p.suffix.lower() in [".safetensors", ".ckpt", ".pt", ".pth"]:
            out.append(
                {
                    "name": p.name,
                    "path": str(p),
                    "gb": round(p.stat().st_size / (1024**3), 3),
                    "modified": p.stat().st_mtime,
                }
            )
    return sorted(out, key=lambda x: x["name"].lower())


def list_outputs(limit: int = 20):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    files = []
    for p in OUTPUT.rglob("*"):
        if p.is_file() and p.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp", ".mp4"]:
            files.append(
                {
                    "name": p.name,
                    "path": str(p),
                    "mb": round(p.stat().st_size / (1024**2), 3),
                    "modified": p.stat().st_mtime,
                }
            )
    files.sort(key=lambda x: x["modified"], reverse=True)
    return files[:limit]


def model_vault_status():
    comfy = ensure_comfy_online(timeout_sec=180)
    checkpoints = _model_files(CHECKPOINTS)
    return {
        "policy": "CPU/RAM only",
        "comfy_url": COMFY_URL,
        "comfy": comfy,
        "paths": {
            "comfy_root": str(COMFY_ROOT),
            "checkpoints": str(CHECKPOINTS),
            "vae": str(VAE),
            "loras": str(LORAS),
            "output": str(OUTPUT),
            "workflows": str(WORKFLOWS),
        },
        "checkpoints": checkpoints,
        "vae": _model_files(VAE),
        "loras": _model_files(LORAS),
        "outputs_recent": list_outputs(10),
        "ready_for_basic_generation": any(m["name"] == DEFAULT_CKPT for m in checkpoints),
        "default_checkpoint": DEFAULT_CKPT,
    }


def basic_workflow(prompt: str, negative: str = "", seed: int | None = None, steps: int = 8, width: int = 384, height: int = 384):
    if seed is None:
        seed = int(time.time()) % 2147483647

    steps = max(4, min(int(steps), 18))
    width = max(256, min(int(width), 640))
    height = max(256, min(int(height), 640))

    width = width - (width % 8)
    height = height - (height % 8)

    negative = negative or "low quality, blurry, watermark, text artifacts, distorted, bad anatomy"

    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": int(seed),
                "steps": steps,
                "cfg": 6.5,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": DEFAULT_CKPT,
            },
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1,
            },
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt,
                "clip": ["4", 1],
            },
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative,
                "clip": ["4", 1],
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2],
            },
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "EZZIO_CPU_SD15",
                "images": ["8", 0],
            },
        },
    }


def queue_basic_generation(
    prompt: str, negative: str = "", seed: int | None = None, steps: int = 8, width: int = 384, height: int = 384
):
    status = model_vault_status()

    if not status["comfy"]["ok"]:
        return {
            "ok": False,
            "error": "ComfyUI offline et autostart impossible.",
            "status": status,
        }

    if not status["ready_for_basic_generation"]:
        return {
            "ok": False,
            "error": f"Checkpoint manquant : {DEFAULT_CKPT}",
            "status": status,
        }

    workflow = basic_workflow(
        prompt=prompt,
        negative=negative,
        seed=seed,
        steps=steps,
        width=width,
        height=height,
    )

    before = list_outputs(20)

    response = httpx.post(
        f"{COMFY_URL}/prompt",
        json={"prompt": workflow},
        timeout=30,
    )

    result = {
        "ok": response.status_code < 400,
        "status_code": response.status_code,
        "request": {
            "prompt": prompt,
            "negative": negative,
            "seed": seed,
            "steps": steps,
            "width": width,
            "height": height,
        },
        "workflow": workflow,
        "comfy_response": None,
        "outputs_before": before,
        "output_note": "ComfyUI génère en arrière-plan. Vérifie /forge/comfy/outputs.",
    }

    try:
        result["comfy_response"] = response.json()
    except Exception:
        result["comfy_response"] = response.text

    return result
