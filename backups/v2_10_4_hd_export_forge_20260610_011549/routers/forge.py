from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
from core.comfy_api import (
    ensure_comfy_online,
    model_vault_status,
    basic_workflow,
    queue_basic_generation,
    list_outputs,
)

router = APIRouter(prefix="/forge", tags=["forge"])

class ComfyGenerateRequest(BaseModel):
    prompt: str
    negative: str = ""
    seed: int | None = None
    steps: int = 8
    width: int = 384
    height: int = 384

@router.get("/status")
async def forge_status():
    return status()

@router.get("/comfy/health")
async def forge_comfy_health():
    return comfy_health()

@router.post("/comfy/wake")
async def forge_comfy_wake():
    return ensure_comfy_online(timeout_sec=180)

@router.get("/comfy/models")
async def forge_comfy_models():
    return model_vault_status()

@router.get("/comfy/outputs")
async def forge_comfy_outputs():
    return {
        "ok": True,
        "outputs": list_outputs(30),
    }

@router.post("/comfy/workflow/basic")
async def forge_comfy_workflow(req: ComfyGenerateRequest):
    return {
        "ok": True,
        "workflow": basic_workflow(
            prompt=req.prompt,
            negative=req.negative,
            seed=req.seed,
            steps=req.steps,
            width=req.width,
            height=req.height,
        ),
    }

@router.post("/comfy/generate-basic")
async def forge_comfy_generate(req: ComfyGenerateRequest):
    result = queue_basic_generation(
        prompt=req.prompt,
        negative=req.negative,
        seed=req.seed,
        steps=req.steps,
        width=req.width,
        height=req.height,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result

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
