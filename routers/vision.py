from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from core.schemas import VisionPathRequest
from core.vision_bridge import analyze_image_file, save_upload_bytes, status

router = APIRouter(prefix="/vision", tags=["vision"])


@router.get("/status")
async def vision_status():
    return status()


@router.post("/analyze-path")
async def analyze_path(req: VisionPathRequest):
    try:
        return analyze_image_file(req.path, prompt=req.prompt, mode=req.mode)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/analyze")
async def analyze_upload(
    file: UploadFile = File(...),
    prompt: str = Form(""),
    mode: str = Form("auto"),
):
    try:
        content = await file.read()
        path = save_upload_bytes(file.filename, content)
        return analyze_image_file(str(path), prompt=prompt, mode=mode)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
