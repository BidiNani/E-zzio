"""
E-ZZIO Web API — Capability Registry Router.
Expose les capacités qualifiées et leur gouvernance via REST.
"""
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.capabilities.registry import capability_registry

router = APIRouter(prefix="/capabilities", tags=["Capabilities"])


class CapabilityExecutionRequest(BaseModel):
    capability_name: str
    parameters: dict[str, Any] = {}


@router.get("")
async def list_all_capabilities():
    """Retourne l'ensemble des capacités enregistrées dans le registre avec leur statut."""
    return {
        "ok": True,
        "capabilities": capability_registry.list_capabilities(),
        "total": len(capability_registry.qualifications)
    }


@router.get("/{name}")
async def get_capability_details(name: str):
    """Retourne la fiche de qualification contractuelle d'une capacité."""
    cap = capability_registry.get_capability(name)
    if not cap:
        raise HTTPException(status_code=404, detail=f"Capacité '{name}' introuvable dans le registre.")
    return {
        "ok": True,
        "qualification": cap.model_dump()
    }


@router.post("/execute")
async def execute_capability_endpoint(req: CapabilityExecutionRequest):
    """Exécute une capacité qualifiée via le sas de sécurité centralisé."""
    res = await capability_registry.execute_capability(req.capability_name, req.parameters)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res)
    return res
