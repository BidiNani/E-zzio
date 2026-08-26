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

from core.hd_forge import (
    list_comfy_images,
    latest_comfy_image,
    upscale_image_to_hd,
    upscale_latest_to_1080p,
    hd_presets,
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


@router.get("/image/hd-presets")
async def forge_hd_presets():
    return hd_presets()


@router.get("/image/list")
async def forge_image_list():
    return {
        "ok": True,
        "images": list_comfy_images(50),
    }


@router.get("/image/latest")
async def forge_image_latest():
    latest = latest_comfy_image()
    return {
        "ok": latest is not None,
        "latest": latest,
    }


class HDUpscaleRequest(BaseModel):
    path: str
    width: int = 1920
    height: int = 1080
    sharpen: bool = True
    output_name: str | None = None


@router.post("/image/upscale-hd")
async def forge_image_upscale_hd(req: HDUpscaleRequest):
    return upscale_image_to_hd(
        source_path=req.path,
        width=req.width,
        height=req.height,
        sharpen=req.sharpen,
        output_name=req.output_name,
    )


@router.post("/image/upscale-latest-1080p")
async def forge_image_upscale_latest():
    return upscale_latest_to_1080p()
