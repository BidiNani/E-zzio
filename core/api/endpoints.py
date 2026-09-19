"""
core/api/endpoints.py — Tous les endpoints REST pour l'UI E-zzio.

Chaque endpoint retourne un JSON structuré :
  { ok: bool, data: ..., error?: str }
"""
import os
import platform
import shutil
from datetime import datetime
from pathlib import Path

import psutil
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.api.state_store import append, delete, load, save, update

router = APIRouter(prefix="/api", tags=["ezzio"])


# ============================================================
# MODELS Pydantic
# ============================================================

class MissionCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "normal"
    status: str = "pending"

class ObjectiveCreate(BaseModel):
    title: str
    key_results: list[str] = []
    progress: int = 0

class ProjectCreate(BaseModel):
    name: str
    path: str = ""
    status: str = "active"

class AutomationCreate(BaseModel):
    name: str
    schedule: str
    command: str
    enabled: bool = True

class ApprovalAction(BaseModel):
    decision: str  # "approve" | "reject"
    reason: str = ""

class SearchQuery(BaseModel):
    query: str
    provider: str = "tavily"
    max_results: int = 5


# ============================================================
# MISSIONS
# ============================================================

@router.get("/missions")
async def list_missions():
    return {"ok": True, "data": load("missions", [])}

@router.post("/missions")
async def create_mission(m: MissionCreate):
    item = append("missions", m.dict())
    return {"ok": True, "data": item}

@router.patch("/missions/{mission_id}")
async def update_mission(mission_id: str, patch: dict):
    item = update("missions", mission_id, patch)
    if not item:
        raise HTTPException(404, "Mission introuvable")
    return {"ok": True, "data": item}

@router.delete("/missions/{mission_id}")
async def delete_mission(mission_id: str):
    if not delete("missions", mission_id):
        raise HTTPException(404, "Mission introuvable")
    return {"ok": True}


# ============================================================
# APPROVALS
# ============================================================

@router.get("/approvals")
async def list_approvals():
    return {"ok": True, "data": load("approvals", [])}

@router.post("/approvals/{approval_id}/decide")
async def decide_approval(approval_id: str, action: ApprovalAction):
    items = load("approvals", [])
    for item in items:
        if item.get("id") == approval_id:
            item["decision"] = action.decision
            item["reason"] = action.reason
            item["decided_at"] = datetime.utcnow().isoformat() + "Z"
            item["status"] = "decided"
            save("approvals", items)
            return {"ok": True, "data": item}
    raise HTTPException(404, "Approbation introuvable")


# ============================================================
# OBJECTIVES
# ============================================================

@router.get("/objectives")
async def list_objectives():
    return {"ok": True, "data": load("objectives", [])}

@router.post("/objectives")
async def create_objective(o: ObjectiveCreate):
    item = append("objectives", o.dict())
    return {"ok": True, "data": item}

@router.delete("/objectives/{obj_id}")
async def delete_objective(obj_id: str):
    if not delete("objectives", obj_id):
        raise HTTPException(404, "Objectif introuvable")
    return {"ok": True}


# ============================================================
# PROJECTS
# ============================================================

@router.get("/projects")
async def list_projects():
    projects = load("projects", [])
    # Auto-découverte : ajouter les sous-dossiers de G:\AI
    if not projects:
        ai_root = Path("G:/AI")
        if ai_root.exists():
            for p in ai_root.iterdir():
                if p.is_dir() and not p.name.startswith("."):
                    projects.append({
                        "id": f"auto-{p.name}",
                        "name": p.name,
                        "path": str(p),
                        "status": "active",
                        "created_at": datetime.utcnow().isoformat() + "Z",
                        "auto": True,
                    })
    return {"ok": True, "data": projects}

@router.post("/projects")
async def create_project(p: ProjectCreate):
    item = append("projects", p.dict())
    return {"ok": True, "data": item}


# ============================================================
# FILES (explorateur read-only sur G:\AI\E-zzio)
# ============================================================

@router.get("/files")
async def list_files(path: str = ""):
    base = Path("G:/AI/E-zzio").resolve()
    target = (base / path).resolve() if path else base
    if not str(target).startswith(str(base)):
        raise HTTPException(403, "Accès en dehors du projet interdit")
    if not target.exists():
        raise HTTPException(404, "Chemin introuvable")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
            if entry.name.startswith(".") or entry.name == "__pycache__":
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry.relative_to(base)).replace("\\", "/"),
                "is_dir": entry.is_dir(),
                "size": 0 if entry.is_dir() else stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
    except PermissionError:
        raise HTTPException(403, "Accès refusé") from None

    return {"ok": True, "data": items, "path": str(target.relative_to(base)).replace("\\", "/") or "."}


@router.get("/files/content")
async def get_file_content(path: str):
    base = Path("G:/AI/E-zzio").resolve()
    target = (base / path).resolve()
    if not str(target).startswith(str(base)):
        raise HTTPException(403, "Accès interdit")
    if not target.exists() or not target.is_file():
        raise HTTPException(404, "Fichier introuvable")
    if target.stat().st_size > 500_000:
        raise HTTPException(413, "Fichier trop volumineux (> 500 Ko)")
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
        return {"ok": True, "content": content, "path": path}
    except Exception as e:
        raise HTTPException(500, str(e)) from e


# ============================================================
# SEARCH (Tavily)
# ============================================================

        # [OBSOLÈTE - remplacé par routers/search.py] @router.post("/search")
async def search(q: SearchQuery):
    if q.provider == "tavily":
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise HTTPException(400, "TAVILY_API_KEY manquante")
        try:
            from core.providers.tavily_provider import TavilyProvider
            provider = TavilyProvider(api_key)
            result = await provider.search(q.query)
            return {"ok": True, "data": result}
        except Exception as e:
            raise HTTPException(500, str(e)) from e
    raise HTTPException(400, f"Provider '{q.provider}' non supporté")


# ============================================================
# AUTOMATIONS
# ============================================================

@router.get("/automations")
async def list_automations():
    return {"ok": True, "data": load("automations", [])}

@router.post("/automations")
async def create_automation(a: AutomationCreate):
    item = append("automations", a.dict())
    return {"ok": True, "data": item}

@router.patch("/automations/{auto_id}")
async def toggle_automation(auto_id: str, patch: dict):
    item = update("automations", auto_id, patch)
    if not item:
        raise HTTPException(404, "Automatisation introuvable")
    return {"ok": True, "data": item}

@router.delete("/automations/{auto_id}")
async def delete_automation(auto_id: str):
    if not delete("automations", auto_id):
        raise HTTPException(404, "Automatisation introuvable")
    return {"ok": True}


# ============================================================
# MEMORY
# ============================================================

@router.get("/memory")
async def list_memory():
    """Liste les artefacts mémoire (fichiers d'audit, snapshots)."""
    memories = []
    roots = [
        Path("G:/AI/E-zzio/state/audit/current"),
        Path("G:/AI/E-zzio/data/models"),
        Path("G:/AI/E-zzio/runtime/state"),
    ]
    for root in roots:
        if not root.exists():
            continue
        for f in root.rglob("*.json"):
            try:
                stat = f.stat()
                memories.append({
                    "name": f.name,
                    "path": str(f.relative_to(Path("G:/AI/E-zzio"))).replace("\\", "/"),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "tier": "L5" if "audit" in str(f) else "L3",
                })
            except Exception:
                continue
    memories.sort(key=lambda x: x["modified"], reverse=True)
    return {"ok": True, "data": memories[:200]}


@router.get("/memory/content")
async def get_memory_content(path: str):
    base = Path("G:/AI/E-zzio").resolve()
    target = (base / path).resolve()
    if not str(target).startswith(str(base)):
        raise HTTPException(403, "Accès interdit")
    if not target.exists():
        raise HTTPException(404, "Fichier introuvable")
    try:
        import json
        with open(target, encoding="utf-8") as f:
            return {"ok": True, "data": json.load(f), "path": path}
    except Exception as e:
        raise HTTPException(500, str(e)) from e


# ============================================================
# HEALTH (étendu)
# ============================================================

@router.get("/health/full")
async def health_full():
    """Health check complet : système + providers + backend."""
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = shutil.disk_usage("G:/")

    # Vérifier Ollama
    ollama_status = "unknown"
    try:
        import httpx
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get("http://localhost:11434/api/tags")
            ollama_status = "online" if r.status_code == 200 else "error"
    except Exception:
        ollama_status = "offline"

    # Vérifier Gemini
    gemini_status = "unknown"
    from core.config.secrets_loader import gemini_keys
    keys = gemini_keys()
    if keys:
        gemini_status = "configured" if len(keys) > 0 else "no_keys"
    else:
        gemini_status = "no_keys"

    return {
        "ok": True,
        "data": {
            "system": {
                "hostname": platform.node(),
                "platform": platform.system(),
                "python": platform.python_version(),
                "cpu_percent": cpu,
                "ram_used_gb": round(mem.used / (1024**3), 2),
                "ram_total_gb": round(mem.total / (1024**3), 2),
                "ram_percent": mem.percent,
                "disk_used_gb": round(disk.used / (1024**3), 2),
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "disk_percent": round(disk.used / disk.total * 100, 1),
            },
            "providers": {
                "ollama": ollama_status,
                "gemini": gemini_status,
                "gemini_keys_count": len(keys) if keys else 0,
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    }


# ============================================================
# KILL SWITCH
# ============================================================

@router.post("/kill")
async def kill_switch():
    """Arrêt d'urgence : enregistre la demande et notifie."""
    event = append("kill_events", {
        "action": "kill_requested",
        "source": "ui",
    })
    # Le backend ne se tue pas lui-même, il enregistre juste l'événement.
    # Un superviseur externe peut réagir à ce fichier.
    return {"ok": True, "data": event, "message": "Kill switch enregistré. Redémarrage manuel requis."}
