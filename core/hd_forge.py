import os
import time
import json
from pathlib import Path
from typing import Optional

from PIL import Image, ImageFilter, ImageOps

PROJECT_ROOT = Path("G:/AI/E-zzio")
COMFY_ROOT = Path("G:/AI/external/ComfyUI")
COMFY_OUTPUT = COMFY_ROOT / "output"
HD_OUTPUT = PROJECT_ROOT / "forge" / "outputs" / "image_hd"

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

COMFY_OUTPUT.mkdir(parents=True, exist_ok=True)
HD_OUTPUT.mkdir(parents=True, exist_ok=True)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

def _safe_image_path(path_text: str) -> Path:
    p = Path(path_text).resolve()

    allowed = [
        COMFY_OUTPUT.resolve(),
        HD_OUTPUT.resolve(),
        (PROJECT_ROOT / "forge").resolve(),
        (PROJECT_ROOT / "workspace").resolve(),
    ]

    if not any(str(p).startswith(str(root)) for root in allowed):
        raise ValueError("Image refusée : hors ComfyUI/output, forge ou workspace.")

    if not p.exists():
        raise FileNotFoundError(str(p))

    if p.suffix.lower() not in IMAGE_EXTS:
        raise ValueError("Format image refusé.")

    return p

def list_comfy_images(limit: int = 30):
    files = []
    for p in COMFY_OUTPUT.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            files.append({
                "name": p.name,
                "path": str(p),
                "mb": round(p.stat().st_size / (1024 ** 2), 3),
                "modified": p.stat().st_mtime,
            })

    files.sort(key=lambda x: x["modified"], reverse=True)
    return files[:max(1, min(int(limit), 200))]

def latest_comfy_image():
    files = list_comfy_images(1)
    return files[0] if files else None

def _fit_16_9(img: Image.Image, width: int, height: int):
    return ImageOps.fit(
        img,
        (width, height),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )

def upscale_image_to_hd(
    source_path: str,
    width: int = 1920,
    height: int = 1080,
    sharpen: bool = True,
    output_name: Optional[str] = None,
):
    src = _safe_image_path(source_path)

    width = max(640, min(int(width), 3840))
    height = max(360, min(int(height), 2160))

    started = time.time()

    with Image.open(src) as im:
        im = im.convert("RGB")

        original = {
            "width": im.width,
            "height": im.height,
            "mode": im.mode,
        }

        up = _fit_16_9(im, width, height)

        if sharpen:
            up = up.filter(ImageFilter.UnsharpMask(radius=1.2, percent=115, threshold=3))

        stamp = time.strftime("%Y%m%d_%H%M%S")
        if not output_name:
            output_name = f"EZZIO_HD_{width}x{height}_{stamp}.png"

        safe_name = Path(output_name).name
        if not safe_name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            safe_name += ".png"

        out = HD_OUTPUT / safe_name
        up.save(out, quality=95)

    result = {
        "ok": True,
        "cpu_ram_only": True,
        "source": str(src),
        "output": str(out),
        "original": original,
        "target": {
            "width": width,
            "height": height,
        },
        "method": "Pillow LANCZOS + optional UnsharpMask",
        "elapsed_ms": int((time.time() - started) * 1000),
    }

    report = HD_OUTPUT / f"{Path(out).stem}.json"
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["report"] = str(report)

    return result

def upscale_latest_to_1080p():
    latest = latest_comfy_image()
    if not latest:
        return {
            "ok": False,
            "error": "Aucune image trouvée dans ComfyUI/output.",
            "comfy_output": str(COMFY_OUTPUT),
        }

    return upscale_image_to_hd(
        source_path=latest["path"],
        width=1920,
        height=1080,
        sharpen=True,
    )

def hd_presets():
    return {
        "cpu_recommended_generation": [
            {"name": "fast_16_9", "width": 384, "height": 216, "steps": 6},
            {"name": "balanced_16_9", "width": 512, "height": 288, "steps": 8},
            {"name": "quality_16_9", "width": 640, "height": 360, "steps": 10},
            {"name": "heavy_16_9", "width": 768, "height": 432, "steps": 12}
        ],
        "final_exports": [
            {"name": "full_hd", "width": 1920, "height": 1080},
            {"name": "qhd", "width": 2560, "height": 1440},
            {"name": "uhd_possible_but_slow", "width": 3840, "height": 2160}
        ],
        "policy": {
            "native_1920_generation": "not recommended on CPU-only",
            "recommended": "generate smaller 16:9 then upscale to 1920x1080",
            "gpu": "not used"
        }
    }
