from fastapi import APIRouter

from core.schemas import CompressRequest
from core.token_compressor import compress_text, estimate_tokens

router = APIRouter(prefix="/compress", tags=["compress"])


@router.post("/text")
async def compress(req: CompressRequest):
    return compress_text(req.text, max_chars=req.max_chars, mode=req.mode)


@router.post("/estimate")
async def estimate(req: CompressRequest):
    return {
        "chars": len(req.text),
        "estimated_tokens": estimate_tokens(req.text),
    }
