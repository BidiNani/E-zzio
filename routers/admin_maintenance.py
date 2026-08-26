from fastapi import APIRouter
from pydantic import BaseModel

from core.project_janitor import (
    maintenance_status,
    audit_project,
    quarantine_dust,
)

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


class DustCleanRequest(BaseModel):
    apply: bool = False


@router.get("/status")
async def get_maintenance_status():
    return maintenance_status()


@router.get("/audit")
async def get_maintenance_audit():
    return audit_project()


@router.post("/dust")
async def post_maintenance_dust(req: DustCleanRequest):
    return quarantine_dust(apply=req.apply)
