from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import HTMLResponse
from typing import List, Dict, Any, Optional
from pathlib import Path

from v17.read_model.service import V17ReadModelService
from v17.read_model.models import (
    SystemOverviewDTO, ModelStatusDTO, TaskItemDTO,
    MemorySummaryDTO, ChannelsStatusDTO, OperationsDTO,
    ProductOverviewDTO
)
from v17.state.models import ProductStateSnapshot
from v17.state.service import product_state_service
from v17.events.models import ProductEvent
from v17.events.buffer import global_event_buffer
from v17.control.models import ActionRequest
from v17.control.service import human_control_plane

from v17.orchestration.intent import intent_engine, StructuredIntent
from v17.orchestration.planner import planner_engine, OrchestrationPlan
from v17.models.intelligence_router import model_intelligence_router, RouteDecision
from v17.models.catalog import ModelProfile

from v17.concurrency.models import UnifiedChannelMessage, ConcurrentTaskRecord, TaskPriority
from v17.concurrency.manager import concurrent_task_manager

router = APIRouter(prefix="/api/v17", tags=["V17 Product Experience"])

_read_service = V17ReadModelService()
_UI_TEMPLATE_PATH = Path(__file__).parent.parent / "ui" / "templates" / "index.html"

@router.get("/product/ui", response_class=HTMLResponse)
async def serve_command_center_ui():
    if _UI_TEMPLATE_PATH.exists():
        return HTMLResponse(content=_UI_TEMPLATE_PATH.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>E-ZZIO Command Center UI</h1>", status_code=200)

@router.get("/product/overview", response_model=ProductOverviewDTO)
async def get_overview():
    return _read_service.get_product_overview()

@router.get("/product/system", response_model=SystemOverviewDTO)
async def get_system():
    return _read_service.get_system_overview()

@router.get("/product/models", response_model=ModelStatusDTO)
async def get_models():
    return _read_service.get_model_status()

@router.get("/product/tasks", response_model=List[TaskItemDTO])
async def get_tasks():
    return _read_service.get_tasks_summary()

@router.get("/product/memory", response_model=MemorySummaryDTO)
async def get_memory():
    return _read_service.get_memory_summary()

@router.get("/product/channels", response_model=ChannelsStatusDTO)
async def get_channels():
    return _read_service.get_channels_status()

@router.get("/product/operations", response_model=OperationsDTO)
async def get_operations():
    return _read_service.get_operations_status()

@router.get("/product/state", response_model=ProductStateSnapshot)
async def get_product_state():
    return product_state_service.get_current_state()

@router.get("/product/events", response_model=List[ProductEvent])
async def get_events(limit: int = Query(50, ge=1, le=500)):
    return global_event_buffer.get_recent(limit=limit)

@router.get("/product/events/recent", response_model=List[ProductEvent])
async def get_events_recent(limit: int = Query(10, ge=1, le=100)):
    return global_event_buffer.get_recent(limit=limit)

# === V17.4 ACTION CONTROL ===
@router.post("/product/actions", response_model=ActionRequest)
async def create_action(payload: Dict[str, Any] = Body(...)):
    return human_control_plane.create_action_request(
        action_type=payload.get("action_type", "GET_SYSTEM_STATE"),
        target=payload.get("target", "system"),
        parameters=payload.get("parameters", {}),
        idempotency_key=payload.get("idempotency_key")
    )

@router.post("/product/actions/{request_id}/approve", response_model=ActionRequest)
async def approve_action(request_id: str):
    try:
        return human_control_plane.approve_action(request_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Action request not found")

@router.post("/product/actions/{request_id}/deny", response_model=ActionRequest)
async def deny_action(request_id: str, reason: str = Query("User denied")):
    try:
        return human_control_plane.deny_action(request_id, reason=reason)
    except ValueError:
        raise HTTPException(status_code=404, detail="Action request not found")

@router.get("/product/actions", response_model=List[ActionRequest])
async def list_actions(limit: int = Query(20, ge=1, le=100)):
    return human_control_plane.list_actions(limit=limit)

# === V17.5 / V17.6 ORCHESTRATION & MODELS ===
@router.post("/orchestration/intent", response_model=StructuredIntent)
async def extract_intent(payload: Dict[str, str] = Body(...)):
    return intent_engine.parse_intent(payload.get("prompt", ""))

@router.post("/orchestration/plan", response_model=OrchestrationPlan)
async def generate_plan(payload: Dict[str, str] = Body(...)):
    return planner_engine.build_plan(payload.get("prompt", ""))

@router.get("/models/available", response_model=List[ModelProfile])
async def list_available_models():
    return model_intelligence_router.get_available_models()

@router.post("/models/routing", response_model=RouteDecision)
async def route_model(payload: Dict[str, Any] = Body(...)):
    return model_intelligence_router.route_for_task(
        payload.get("task_type", "CHAT"),
        payload.get("context_len", 1000),
        payload.get("prefer_local", True)
    )

@router.get("/models/health", response_model=Dict[str, str])
async def get_models_health():
    return model_intelligence_router.get_health_metrics()

# === V17.7 CONCURRENCY & MULTI-CHANNEL ===
@router.post("/concurrency/tasks", response_model=ConcurrentTaskRecord)
async def submit_concurrent_task(payload: UnifiedChannelMessage):
    return concurrent_task_manager.submit_task(payload)

@router.get("/concurrency/tasks", response_model=List[ConcurrentTaskRecord])
async def list_concurrent_tasks(limit: int = Query(50, ge=1, le=100)):
    return concurrent_task_manager.list_tasks(limit=limit)

@router.get("/concurrency/tasks/{task_id}", response_model=ConcurrentTaskRecord)
async def get_concurrent_task(task_id: str):
    t = concurrent_task_manager.get_task(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    return t

@router.post("/concurrency/tasks/{task_id}/cancel")
async def cancel_concurrent_task(task_id: str):
    ok = concurrent_task_manager.cancel_task(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task cannot be cancelled or not found")
    return {"status": "CANCELLED", "task_id": task_id}
