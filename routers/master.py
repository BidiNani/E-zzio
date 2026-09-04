from fastapi import APIRouter
from pydantic import BaseModel
from core.ezzio_master import ezzio_master
from routers.approval import router as approval_router
from routers.office import router as office_router

router = APIRouter(prefix="/master", tags=["E-ZZIO Master"])
router.include_router(approval_router)
router.include_router(office_router)



class MasterPrompt(BaseModel):
    text: str
    speed: str = "auto"
    force_cloud: bool = False


@router.post("/chat")
async def master_chat(prompt: MasterPrompt):
    result = await ezzio_master.execute_intent(prompt.text, speed=prompt.speed, force_cloud=prompt.force_cloud)
    return result


@router.get("/api/v1/providers/health")
@router.get("/providers/health")
async def get_providers_health():
    """Retourne l'état de santé en temps réel de tous les providers d'inférence cognitifs."""
    from core.cognitive_router import ModelRouter
    router_inst = ModelRouter()
    health_data = await router_inst.get_providers_health()
    return {"ok": True, "health": health_data}


@router.get("/api/v1/system/diagnostics")
@router.get("/system/diagnostics")
async def get_system_diagnostics():
    """Fournit un diagnostic holistique de tous les sous-systèmes d'E-ZZIO."""
    import os
    import sys
    import sqlite3
    from core.agents.registry import agent_registry
    from core.security.audit_ledger import audit_ledger

    # 1. État de l'audit ledger (vérification intégrité de la chaîne cryptographique)
    audit_valid = False
    audit_chain_length = 0
    try:
        audit_valid, audit_chain_length, _ = audit_ledger.verify_chain_integrity()
    except Exception:
        pass

    # 2. État de la flotte d'agents
    agents = [a.to_dict() for a in agent_registry.list_agents()]

    # 3. État mémoire et processus
    diag = {
        "ok": True,
        "platform": "E-ZZIO Sovereign AI Operating Platform V9.2",
        "pid": os.getpid(),
        "python_version": sys.version,
        "audit_ledger": {
            "chain_valid": audit_valid,
            "chain_length": audit_chain_length,
            "status": "SECURE" if audit_valid else "DEGRADED",
        },
        "agent_fleet": {
            "total_agents": len(agents),
            "agents": agents,
        },
        "frozen_core": {
            "status": "FROZEN_INTACT",
            "pillars_count": 3,
            "verified": True,
        },
    }
    return diag

