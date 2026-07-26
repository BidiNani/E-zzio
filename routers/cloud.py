from fastapi import APIRouter, HTTPException
from core.schemas import CloudGetRequest
from core.cloud_connectors import (
    github_get,
    reddit_get,
    blizzard_get,
    connectors_status,
)

router = APIRouter(prefix="/cloud", tags=["cloud"])

@router.get("/status")
async def cloud_status():
    return connectors_status()

@router.post("/get")
async def cloud_get(req: CloudGetRequest):
    provider = req.provider.lower().strip()

    try:
        if provider == "github":
            return github_get(req.path, req.params)
        if provider == "reddit":
            return reddit_get(req.path, req.params)
        if provider in ["blizzard", "wow", "battle.net", "battlenet"]:
            return blizzard_get(req.path, req.params)

        raise HTTPException(status_code=400, detail="Provider refusé. Utilise github, reddit ou blizzard.")
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
