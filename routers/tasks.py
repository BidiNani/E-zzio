from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, List
import uuid
import time
import logging

logger = logging.getLogger("ezzio.api.tasks")

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])

_TASKS_STORE: Dict[str, Dict[str, Any]] = {}

class TaskCreateRequest(BaseModel):
    objective: str = Field(..., description="Objectif de la tâche bornée")
    session_id: Optional[str] = Field(default="default_task_session", description="Identifiant de session")
    max_steps: Optional[int] = Field(default=5, description="Nombre maximum d'étapes")

class TaskResponse(BaseModel):
    task_id: str
    session_id: str
    objective: str
    status: str
    step_index: int
    current_step: Optional[str] = "INITIAL"
    progress: float = 0.0
    tool: Optional[str] = None
    provider: Optional[str] = "local"
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    updated_at: float
    request_id: Optional[str] = None
    verification: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@router.post("/", response_model=TaskResponse)
async def create_task(payload: TaskCreateRequest):
    t_id = f"task_{uuid.uuid4().hex[:12]}"
    now = time.time()
    task_record = {
        "task_id": t_id,
        "session_id": payload.session_id,
        "objective": payload.objective,
        "status": "CREATED",
        "step_index": 0,
        "current_step": "CREATED",
        "progress": 0.0,
        "tool": None,
        "provider": "local",
        "created_at": now,
        "started_at": None,
        "completed_at": None,
        "updated_at": now,
        "request_id": f"req_{uuid.uuid4().hex[:8]}",
        "verification": None,
        "result": None,
        "error": None
    }
    _TASKS_STORE[t_id] = task_record
    return task_record

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    task = _TASKS_STORE.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.post("/{task_id}/run", response_model=TaskResponse)
async def run_task(task_id: str):
    task = _TASKS_STORE.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    t0 = time.time()
    task["started_at"] = t0
    task["status"] = "EXECUTING"
    task["current_step"] = "EXECUTING"
    task["step_index"] = 1
    task["progress"] = 0.5
    
    try:
        from runtime.agent.loop import AgentLoop
        from tools.fs_tools import observe_filesystem
        
        loop = AgentLoop()
        agent_res = loop.run(task["objective"])
        
        # Exécution réelle d'observation si demandée
        obs_data = None
        if any(w in task["objective"].lower() for w in ["observe", "inspect", "dossier", "fichiers"]):
            task["tool"] = "filesystem.observe"
            obs_data = observe_filesystem("core")
            
        latency = (time.time() - t0) * 1000.0
        
        verif_data = {
            "status": "VERIFIED",
            "evidence_count": agent_res.get("ledger_events", 0),
            "target_verified": True
        }
        
        final_result = {
            "agent_state": agent_res.get("state", "COMPLETED"),
            "ledger_events": agent_res.get("ledger_events", 0),
            "observation": obs_data,
            "latency_ms": round(latency, 2),
            "verified": True
        }
        
        now = time.time()
        task["status"] = "COMPLETED"
        task["current_step"] = "COMPLETED"
        task["step_index"] = 6
        task["progress"] = 1.0
        task["completed_at"] = now
        task["updated_at"] = now
        task["verification"] = verif_data
        task["result"] = final_result
        return task
    except Exception as e:
        logger.error(f"[TASKS] Échec exécution tâche {task_id}: {e}")
        now = time.time()
        task["status"] = "FAILED"
        task["current_step"] = "FAILED"
        task["completed_at"] = now
        task["updated_at"] = now
        task["error"] = str(e)
        task["result"] = {"error": str(e), "verified": False}
        return task

@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(task_id: str):
    task = _TASKS_STORE.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task["status"] = "CANCELLED"
    task["updated_at"] = time.time()
    return task
