from fastapi import APIRouter, HTTPException

from core.schemas import (
    ImagePromptRequest,
    VideoPlanRequest,
    VideoFromFolderRequest,
    MobileManifestRequest,
)
from core.creative_forge import (
    status,
    comfy_health,
    make_image_prompt,
    make_video_plan,
    ffmpeg_make_video_from_folder,
    apk_status,
    write_mobile_manifest,
)

router = APIRouter(prefix="/forge", tags=["forge"])

@router.get("/status")
async def forge_status():
    return status()

@router.get("/comfy/health")
async def forge_comfy_health():
    return comfy_health()

@router.post("/image/prompt")
async def image_prompt(req: ImagePromptRequest):
    return make_image_prompt(req.prompt, style=req.style, negative=req.negative)

@router.post("/video/plan")
async def video_plan(req: VideoPlanRequest):
    return make_video_plan(req.prompt, duration_sec=req.duration_sec, fps=req.fps, style=req.style)

@router.post("/video/from-folder")
async def video_from_folder(req: VideoFromFolderRequest):
    result = ffmpeg_make_video_from_folder(req.folder, fps=req.fps, output_name=req.output_name)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result

@router.get("/apk/status")
async def forge_apk_status():
    return apk_status()

@router.post("/apk/manifest")
async def forge_apk_manifest(req: MobileManifestRequest):
    return write_mobile_manifest(app_name=req.app_name, app_id=req.app_id)
