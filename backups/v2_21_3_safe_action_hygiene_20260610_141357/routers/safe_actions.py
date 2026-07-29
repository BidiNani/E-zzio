from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict

from core.safe_actions import (
    status,
    registry,
    propose_action,
    queue,
    run_proposal,
    quick_action,
)

router = APIRouter(prefix="/safe-actions", tags=["safe-actions"])

class ProposeRequest(BaseModel):
    action: str
    params: Dict[str, Any] = {}
    reason: str = ""

class RunRequest(BaseModel):
    proposal_id: str
    confirmation: str = ""

class QuickRequest(BaseModel):
    action: str
    params: Dict[str, Any] = {}

@router.get("/status")
async def get_safe_actions_status():
    return status()

@router.get("/registry")
async def get_safe_actions_registry():
    return registry()

@router.get("/queue")
async def get_safe_actions_queue(limit: int = 50):
    return queue(limit=limit)

@router.post("/propose")
async def post_safe_actions_propose(req: ProposeRequest):
    return propose_action(action=req.action, params=req.params, reason=req.reason)

@router.post("/run")
async def post_safe_actions_run(req: RunRequest):
    return run_proposal(proposal_id=req.proposal_id, confirmation=req.confirmation)

@router.post("/quick")
async def post_safe_actions_quick(req: QuickRequest):
    return quick_action(action=req.action, params=req.params)
