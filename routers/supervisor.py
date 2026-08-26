from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from core.supervisor import (
    supervisor_status,
    write_snapshot,
    recent_snapshots,
    watchdog_once,
    mobile_home_html,
)

router = APIRouter(prefix="/supervisor", tags=["supervisor"])


@router.get("/status")
async def supervisor_get_status():
    return supervisor_status()


@router.post("/snapshot")
async def supervisor_post_snapshot():
    return write_snapshot()


@router.get("/snapshots")
async def supervisor_get_snapshots(limit: int = 20):
    return recent_snapshots(limit=limit)


@router.get("/watchdog")
async def supervisor_get_watchdog():
    return watchdog_once()


@router.get("/mobile-home", response_class=HTMLResponse)
async def supervisor_mobile_home():
    return mobile_home_html()
