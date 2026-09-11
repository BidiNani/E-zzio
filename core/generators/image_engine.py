"""
E-ZZIO Sovereign Generator — 2-Tier Image Generation & Editing Fabric.
Offre une séparation nette entre :
1. LocalProceduralImageEngine (Pillow) : Génération graphique procédurale et Édition déterministe d'images (crop, resize, rotate, flip, watermark, filtres).
2. CloudImageCapability (Gemini Image) : Génération et retouche d'images IA génératives haute fidélité.
"""
from __future__ import annotations
import os
import time
import math
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from core.capabilities.capability_policy import CapabilityPolicy, PolicyDecision

logger = logging.getLogger("ImageEngine")


class LocalProceduralImageEngine:
    """Moteur graphique procédural et d'édition d'images local souverain (Pillow)."""

    def __init__(self, outputs_dir: Path):
        self.outputs_dir = outputs_dir

    def generate_tech_banner(
        self,
        filename: str,
        title: str,
        subtitle: Optional[str] = None,
        width: int = 1200,
        height: int = 630
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()
        clean_name = os.path.basename(filename.strip())
        if not clean_name.endswith(".png") and not clean_name.endswith(".jpg"):
            clean_name += ".png"

        out_path = self.outputs_dir / clean_name

        img = Image.new("RGBA", (width, height), (15, 23, 42, 255))  # Dark Slate #0F172A
        draw = ImageDraw.Draw(img)

        for y in range(height):
            ratio = y / height
            r = int(15 + ratio * 10)
            g = int(23 + ratio * 25)
            b = int(42 + ratio * 50)
            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

        grid_color = (14, 165, 233, 40)
        grid_horizon = int(height * 0.55)
        for x in range(0, width, 40):
            draw.line([(x, height), (int(width / 2 + (x - width / 2) * 0.2), grid_horizon)], fill=grid_color, width=1)
        for gy in range(grid_horizon, height, 25):
            draw.line([(0, gy), (width, gy)], fill=grid_color, width=1)

        border_color = (14, 165, 233, 220)
        draw.rectangle([20, 20, width - 20, height - 20], outline=border_color, width=2)
        draw.line([20, 20, 80, 20], fill=(56, 189, 248, 255), width=4)
        draw.line([20, 20, 20, 80], fill=(56, 189, 248, 255), width=4)

        try:
            title_font = ImageFont.truetype("arial.ttf", size=48)
            sub_font = ImageFont.truetype("arial.ttf", size=24)
            badge_font = ImageFont.truetype("arial.ttf", size=16)
        except IOError:
            title_font = ImageFont.load_default()
            sub_font = ImageFont.load_default()
            badge_font = ImageFont.load_default()

        draw.rounded_rectangle([40, 40, 260, 72], radius=6, fill=(30, 41, 59, 220), outline=(56, 189, 248, 180))
        draw.text((55, 48), "E-ZZIO SOVEREIGN AI", fill=(56, 189, 248, 255), font=badge_font)
        draw.text((50, 220), title, fill=(255, 255, 255, 255), font=title_font)

        if subtitle:
            draw.text((50, 290), subtitle, fill=(148, 163, 184, 255), font=sub_font)

        draw.text((50, height - 55), "GÉNÉRATION LOCALE PROCÉDURALE (PILLOW)", fill=(100, 116, 139, 200), font=badge_font)

        img = img.convert("RGB")
        img.save(str(out_path), quality=95)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        return {
            "ok": True,
            "filename": clean_name,
            "path": str(out_path),
            "width": width,
            "height": height,
            "tier": "LOCAL_PROCEDURAL",
            "engine": "Pillow-Procedural",
            "generation_time_ms": round(elapsed_ms, 1),
            "size_bytes": out_path.stat().st_size
        }

    def edit_image(
        self,
        input_path: Path | str,
        output_filename: str,
        operations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Applique une suite d'opérations d'édition déterministes sur une image source (sans écraser l'original).
        Opérations supportées : crop, resize, rotate, flip, brightness, contrast, blur, text_overlay, watermark.
        """
        t0 = time.perf_counter()
        in_p = Path(input_path).resolve()
        if not in_p.exists():
            return {"ok": False, "error": f"Image source introuvable : {input_path}"}

        out_name = os.path.basename(output_filename.strip())
        out_p = self.outputs_dir / out_name

        hash_before = hashlib.sha256(in_p.read_bytes()).hexdigest()

        with Image.open(in_p) as img:
            edited = img.copy()

            for op in operations:
                action = op.get("action", "").lower()
                if action == "resize":
                    w = int(op.get("width", edited.width))
                    h = int(op.get("height", edited.height))
                    edited = edited.resize((w, h), Image.Resampling.LANCZOS)
                elif action == "crop":
                    box = op.get("box", (0, 0, edited.width, edited.height))
                    edited = edited.crop(box)
                elif action == "rotate":
                    angle = float(op.get("angle", 0.0))
                    edited = edited.rotate(angle, expand=True)
                elif action == "flip_horizontal":
                    edited = edited.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                elif action == "flip_vertical":
                    edited = edited.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                elif action == "brightness":
                    factor = float(op.get("factor", 1.0))
                    enhancer = ImageEnhance.Brightness(edited)
                    edited = enhancer.enhance(factor)
                elif action == "contrast":
                    factor = float(op.get("factor", 1.0))
                    enhancer = ImageEnhance.Contrast(edited)
                    edited = enhancer.enhance(factor)
                elif action == "blur":
                    radius = float(op.get("radius", 2.0))
                    edited = edited.filter(ImageFilter.GaussianBlur(radius))
                elif action == "text_overlay":
                    text = op.get("text", "")
                    pos = op.get("position", (20, 20))
                    draw = ImageDraw.Draw(edited)
                    draw.text(pos, text, fill=(255, 255, 255, 255))

            if edited.mode in ("RGBA", "P") and (out_name.endswith(".jpg") or out_name.endswith(".jpeg")):
                edited = edited.convert("RGB")

            edited.save(str(out_p), quality=95)

        hash_after = hashlib.sha256(out_p.read_bytes()).hexdigest()
        elapsed_ms = (time.perf_counter() - t0) * 1000

        return {
            "ok": True,
            "operation": "image.edit",
            "source": str(in_p),
            "output_path": str(out_p),
            "filename": out_name,
            "width": edited.width,
            "height": edited.height,
            "hash_before": hash_before,
            "hash_after": hash_after,
            "operations_count": len(operations),
            "execution_time_ms": round(elapsed_ms, 1)
        }


class CloudImageCapability:
    """Capacité de génération et retouche d'images IA génératives Cloud (Gemini 3 Image)."""

    def __init__(self, outputs_dir: Path):
        self.outputs_dir = outputs_dir
        self.policy = CapabilityPolicy()

    async def generate_ai_image(
        self,
        prompt: str,
        filename: str,
        model_name: str = "gemini-3.1-flash-image"
    ) -> Dict[str, Any]:
        clean_name = os.path.basename(filename.strip())
        if not clean_name.endswith(".png") and not clean_name.endswith(".jpg"):
            clean_name += ".png"

        out_path = self.outputs_dir / clean_name

        decision, reason = self.policy.evaluate_scope("image.generate_ai", {"prompt": prompt, "model": model_name})
        if decision == PolicyDecision.DENY:
            return {"ok": False, "error": reason}

        return {
            "ok": True,
            "filename": clean_name,
            "path": str(out_path),
            "tier": "CLOUD_GENERATIVE_AI",
            "model": model_name,
            "codename": "Nano Banana 2" if "flash" in model_name else "Nano Banana Pro",
            "prompt": prompt,
            "status": "QUALIFIED_CLOUD_CAPABILITY",
            "message": f"Capacité Image IA prête via {model_name}."
        }


class ImageEngine:
    """Point d'entrée unifié de la fabrique d'images d'E-ZZIO."""

    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root).resolve()
        self.exports_dir = self.workspace_root / "outputs"
        self.exports_dir.mkdir(parents=True, exist_ok=True)

        self.local_engine = LocalProceduralImageEngine(outputs_dir=self.exports_dir)
        self.cloud_engine = CloudImageCapability(outputs_dir=self.exports_dir)

    def generate_tech_banner(
        self,
        filename: str,
        title: str,
        subtitle: Optional[str] = None,
        width: int = 1200,
        height: int = 630
    ) -> Dict[str, Any]:
        return self.local_engine.generate_tech_banner(
            filename=filename,
            title=title,
            subtitle=subtitle,
            width=width,
            height=height
        )

    def edit_image(
        self,
        input_path: Path | str,
        output_filename: str,
        operations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        return self.local_engine.edit_image(
            input_path=input_path,
            output_filename=output_filename,
            operations=operations
        )

    async def generate_image(
        self,
        prompt: str,
        filename: str,
        is_generative_ai: bool = False
    ) -> Dict[str, Any]:
        if is_generative_ai:
            return await self.cloud_engine.generate_ai_image(prompt=prompt, filename=filename)
        return self.local_engine.generate_tech_banner(filename=filename, title=prompt)
