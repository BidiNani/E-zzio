"""
E-ZZIO Web API — HITL Approval Router.
Expose la gestion des approbations humaines sous contrôle strict sans secret.
"""
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from core.governance.approval import (
    ApprovalExpiredError,
    DecisionChoice,
    StateTransitionError,
    approval_manager,
)

router = APIRouter(tags=["Approvals"])



class PendingApprovalItem(BaseModel):
    approval_id: str
    task_id: str
    capability_name: str
    scope: str
    safe_summary: str
    requested_at: str
    expires_at: str
    time_remaining_sec: int
    status: str


class PendingApprovalsResponse(BaseModel):
    ok: bool = True
    pending_approvals: list[PendingApprovalItem]
    total: int


class DecideRequest(BaseModel):
    decision: DecisionChoice
    decided_by: str = Field(..., min_length=1)
    reason: str | None = None


class DecideResponse(BaseModel):
    ok: bool = True
    approval_id: str
    status: str
    decided_by: str
    decided_at: str
    reason: str | None = None


def _calculate_remaining_sec(expires_at_str: str) -> int:
    try:
        exp_dt = datetime.fromisoformat(expires_at_str)
        now_dt = datetime.now(UTC)
        diff = int((exp_dt - now_dt).total_seconds())
        return max(0, diff)
    except Exception:
        return 0


@router.get("/api/v1/approvals/pending", response_model=PendingApprovalsResponse)
@router.get("/approvals/pending", response_model=PendingApprovalsResponse)
async def list_pending_approvals():
    """
    Retourne uniquement les demandes en attente valides.
    Aucun paramètre secret (params_payload, token, credentials) n'est exposé.
    """
    pending = approval_manager.get_pending()
    items = [
        PendingApprovalItem(
            approval_id=req.approval_id,
            task_id=req.task_id,
            capability_name=req.capability_name,
            scope=req.scope,
            safe_summary=req.safe_summary,
            requested_at=req.requested_at,
            expires_at=req.expires_at,
            time_remaining_sec=_calculate_remaining_sec(req.expires_at),
            status=req.status.value,
        )
        for req in pending
    ]
    return PendingApprovalsResponse(
        ok=True,
        pending_approvals=items,
        total=len(items),
    )


@router.post("/api/v1/approvals/{approval_id}/decide", response_model=DecideResponse)
@router.post("/approvals/{approval_id}/decide", response_model=DecideResponse)
async def decide_approval(approval_id: str, body: DecideRequest):
    """
    Enregistre une décision humaine (APPROVE ou REJECT).
    Rejette toute tentative de forcer un statut système (EXPIRED, CONSUMED, CANCELLED).
    """
    try:
        updated = approval_manager.decide(
            approval_id=approval_id,
            choice=body.decision,
            decided_by=body.decided_by,
            reason=body.reason,
        )
        return DecideResponse(
            ok=True,
            approval_id=updated.approval_id,
            status=updated.status.value,
            decided_by=updated.decided_by or body.decided_by,
            decided_at=updated.decided_at or "",
            reason=updated.decision_reason,
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Demande d'approbation inconnue : {approval_id}",
        ) from None
    except ApprovalExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=str(exc),
        ) from exc
    except StateTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors du traitement de l'approbation : {exc}",
        ) from exc
