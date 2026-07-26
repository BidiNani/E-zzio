from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel

from core.smart_vision import analyze_path, save_upload

router = APIRouter(tags=["vision-smart"])

class SmartVisionPathRequest(BaseModel):
    path: str
    prompt: str = ""

@router.get("/vision-smart/status")
async def vision_smart_status():
    return {
        "ok": True,
        "version": "v2.30.2-smart-vision",
        "endpoints": [
            "/vision/analyze-smart",
            "/vision/analyze-smart-path",
            "/vision-smart/status"
        ],
        "policy": {
            "cpu_ram_only": True,
            "gpu": "untouched",
            "no_ads": True,
            "no_powershell_unless_technical_screenshot": True
        }
    }

@router.post("/vision/analyze-smart-path")
async def analyze_smart_path(req: SmartVisionPathRequest):
    return analyze_path(req.path, req.prompt)

@router.post("/vision/analyze-smart")
async def analyze_smart_upload(
    file: UploadFile = File(...),
    prompt: str = Form("")
):
    content = await file.read()
    target = save_upload(file.filename or "image.png", content)
    return analyze_path(str(target), prompt)
