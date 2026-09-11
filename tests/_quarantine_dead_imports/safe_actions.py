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
    cancel_proposal,
    cancel_pending,
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


class CancelRequest(BaseModel):
    proposal_id: str
    reason: str = "annulation manuelle"


class CancelPendingRequest(BaseModel):
    reason: str = "nettoyage file pending"


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


@router.post("/cancel")
async def post_safe_actions_cancel(req: CancelRequest):
    return cancel_proposal(proposal_id=req.proposal_id, reason=req.reason)


@router.post("/cancel-pending")
async def post_safe_actions_cancel_pending(req: CancelPendingRequest):
    return cancel_pending(reason=req.reason)
