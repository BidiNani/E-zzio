"""E-ZZIO FastAPI Router — Universal Perception Endpoints."""
from __future__ import annotations
import os
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from core.perception.unified_perception import UnifiedPerceptionPipeline

router = APIRouter(prefix="/perception", tags=["perception"])
pipeline = UnifiedPerceptionPipeline()

UPLOAD_DIR = Path("G:/AI/E-zzio/runtime/inbox")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class PerceptionRequest(BaseModel):
    target: str  # URL ou chemin ou texte
    prompt: str = ""
    mode: str = "auto"  # "auto", "batch", "streaming"
    session_id: str = "default"


@router.get("/status")
async def perception_status():
    """Statut de la couche de perception universelle."""
    return {
        "ok": True,
        "status": "OPERATIONAL",
        "capabilities": [
            "universal_file_reader",
            "safe_web_fetcher",
            "vision_ocr_qwen2.5vl",
            "whisper_audio_batch",
            "nemotron_asr_streaming",
            "qr_engine_opencv"
        ]
    }


@router.post("/perceive")
async def perceive_target(req: PerceptionRequest):
    """Perception universelle d'une URL, chemin de fichier ou texte."""
    try:
        res = await pipeline.perceive(
            req.target,
            user_prompt=req.prompt,
            mode=req.mode,
            session_id=req.session_id
        )
        return res
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/upload")
async def upload_and_perceive(
    file: UploadFile = File(...),
    prompt: str = Form(""),
):
    """Téléverse un fichier (PDF, image, audio, doc) et extrait son contenu immédiatement."""
    try:
        target_path = UPLOAD_DIR / file.filename
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        res = await pipeline.perceive(target_path, user_prompt=prompt)
        return res
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
