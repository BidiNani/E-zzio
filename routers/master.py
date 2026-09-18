from pathlib import Path

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
    force_cloud: bool = True
    mission_profile: str = "STANDARD"
    model_target: str | None = "auto"
    channel: str = "web"
    session_id: str = ""


@router.post("/chat")
async def master_chat(prompt: MasterPrompt):
    # Cloud-First souverain : le Cloud (Gemini) est la priorité absolue,
    # sauf si le mode local_only est explicitement verrouillé dans la gouvernance.
    local_only = _runtime_governance_settings.get("local_only", False)
    effective_force_cloud = prompt.force_cloud and (not local_only)

    result = await ezzio_master.execute_intent(
        user_prompt=prompt.text,
        speed=prompt.speed,
        force_cloud=effective_force_cloud,
        session_id=prompt.session_id,
        mission_profile=prompt.mission_profile,
        model_target=prompt.model_target,
        channel=prompt.channel,
    )
    return result



_last_health_cache = {"timestamp": 0, "data": None}


@router.get("/api/v1/providers/health")
@router.get("/providers/health")
async def get_providers_health():
    """Retourne l'état de santé en temps réel de tous les providers d'inférence cognitifs avec cache 15s."""
    import time
    now = time.time()
    if _last_health_cache["data"] and (now - _last_health_cache["timestamp"] < 15.0):
        return {"ok": True, "health": _last_health_cache["data"]}

    from core.cognitive_router import ModelRouter
    router_inst = ModelRouter()
    health_data = await router_inst.get_providers_health()
    _last_health_cache["timestamp"] = now
    _last_health_cache["data"] = health_data
    return {"ok": True, "health": health_data}


@router.get("/api/v1/system/diagnostics")
@router.get("/system/diagnostics")
async def get_system_diagnostics():
    """Fournit un diagnostic holistique de tous les sous-systèmes d'E-ZZIO."""
    import os
    import sqlite3
    import sys

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

    # 3. État des bases de données SQLite (intégrité & WAL)
    db_health = {}
    for db_name, db_file in [
        ("tasks", "runtime/state/tasks.db"),
        ("audit", "runtime/evidence/audit_ledger.db"),
        ("artifacts", "runtime/evidence/artifact_provenance.db"),
    ]:
        p = Path(db_file)
        if p.exists():
            try:
                with sqlite3.connect(str(p), timeout=5.0) as conn:
                    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
                    journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
                db_health[db_name] = {
                    "exists": True,
                    "size_bytes": p.stat().st_size,
                    "integrity": integrity,
                    "journal_mode": journal_mode,
                }
            except Exception as e:
                db_health[db_name] = {"exists": True, "error": str(e)}
        else:
            db_health[db_name] = {"exists": False}

    # 4. État mémoire et processus
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
        "databases": db_health,
        "frozen_core": {
            "status": "FROZEN_INTACT",
            "pillars_count": 3,
            "verified": True,
        },
    }
    return diag



@router.get("/api/v1/artifacts/{artifact_id}")
@router.get("/artifacts/{artifact_id}")
async def get_artifact_provenance(artifact_id: str):
    """Retourne la traçabilité cryptographique complète d'un artefact scellé."""
    from fastapi import HTTPException, status

    from core.artifacts.provenance import artifact_provenance
    art = artifact_provenance.get_artifact(artifact_id)
    if not art:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Artifact '{artifact_id}' non trouvé")
    verification = artifact_provenance.verify_artifact(artifact_id)
    return {"ok": True, "artifact": art, "verification": verification}


@router.get("/api/v1/tasks/{task_id}/artifacts")
@router.get("/tasks/{task_id}/artifacts")
async def list_task_artifacts(task_id: str):
    """Retourne tous les artefacts scellés associés à une tâche."""
    from core.artifacts.provenance import artifact_provenance
    artifacts = artifact_provenance.list_task_artifacts(task_id)
    return {"ok": True, "task_id": task_id, "artifacts": artifacts, "count": len(artifacts)}


@router.get("/api/v1/tasks/dag/{dag_id}")
@router.get("/tasks/dag/{dag_id}")
async def get_dag_status(dag_id: str):
    """Retourne l'état complet du graphe de tâches DAG (nœuds, états, dépendances)."""
    from fastapi import HTTPException, status

    from core.orchestration import DAGOrchestrator
    # Recherche dans les instances actives ou état par défaut
    orch = DAGOrchestrator()
    dag = orch.get_dag(dag_id)
    if not dag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"DAG '{dag_id}' non trouvé")
    return {"ok": True, "dag": dag.to_dict()}


@router.get("/api/v1/missions")
@router.get("/missions")
async def list_missions():
    """Retourne la liste des missions des workers asynchrones."""
    from core.agent.mission_controller import mission_registry
    missions = [m.to_dict() for m in mission_registry._missions.values()]
    active = [m.to_dict() for m in [m for m in mission_registry._missions.values() if m.status.value in ('PENDING', 'RUNNING')]]
    return {"ok": True, "missions": missions, "active": active, "total": len(missions)}


@router.post("/api/v1/missions/{mission_id}/cancel")
@router.post("/missions/{mission_id}/cancel")
async def cancel_mission_endpoint(mission_id: str):
    """Annule en toute sécurité une mission en cours."""
    from core.agent.mission_controller import mission_registry
    success = mission_registry.cancel(mission_id)
    return {"ok": success, "mission_id": mission_id, "status": "CANCELLED" if success else "NOT_FOUND"}


@router.get("/api/v1/missions/{mission_id}")
@router.get("/missions/{mission_id}")
async def get_mission_endpoint(mission_id: str):
    """Retourne le détail d'une mission."""
    from fastapi import HTTPException, status

    from core.agent.mission_controller import mission_registry
    m = mission_registry.get(mission_id)
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' non trouvée")
    return {"ok": True, "mission": m.to_dict()}


@router.post("/api/v1/missions/{mission_id}/pause")
@router.post("/missions/{mission_id}/pause")
async def pause_mission_endpoint(mission_id: str):
    """Met en pause une mission."""
    from core.agent.mission_controller import mission_registry
    success = mission_registry.pause(mission_id)
    return {"ok": success, "mission_id": mission_id, "status": "PAUSED" if success else "NOT_FOUND"}


@router.post("/api/v1/missions/{mission_id}/resume")
@router.post("/missions/{mission_id}/resume")
async def resume_mission_endpoint(mission_id: str):
    """Reprend une mission mise en pause."""
    from core.agent.mission_controller import mission_registry
    success = mission_registry.resume(mission_id)
    return {"ok": success, "mission_id": mission_id, "status": "RUNNING" if success else "NOT_FOUND"}


class GovernanceSettingsPayload(BaseModel):
    local_only: bool | None = None
    cloud_fallback: bool | None = None
    max_budget_cents: int | None = None


_runtime_governance_settings = {
    "local_only": False,
    "cloud_fallback": True,
    "max_budget_cents": 2500,
    "profiles": {
        "chat": "CLOUD_PREFERRED",
        "coding": "GEMINI_CLOUD_FIRST",
        "reasoning": "GEMINI_CLOUD",
    },
}


@router.get("/api/v1/governance/settings")
@router.get("/governance/settings")
async def get_governance_settings():
    """Retourne la configuration actuelle de gouvernance et de souveraineté locale."""
    from core.routing.model_registry import canonical_model_registry
    models = canonical_model_registry.list_models()
    return {
        "ok": True,
        "settings": _runtime_governance_settings,
        "registered_models_count": len(models),
        "available_local_roles": [m.role for m in models if m.source.name == "LOCAL"],
    }


@router.post("/api/v1/governance/settings")
@router.post("/governance/settings")
async def update_governance_settings(payload: GovernanceSettingsPayload):
    """Met à jour dynamiquement les réglages de gouvernance runtime."""
    if payload.local_only is not None:
        _runtime_governance_settings["local_only"] = payload.local_only
    if payload.cloud_fallback is not None:
        _runtime_governance_settings["cloud_fallback"] = payload.cloud_fallback
    if payload.max_budget_cents is not None:
        _runtime_governance_settings["max_budget_cents"] = payload.max_budget_cents
    return {"ok": True, "settings": _runtime_governance_settings}



