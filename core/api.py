"""core/api.py - Routeur FastAPI avec streaming SSE et exécution orchestrée."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import AsyncGenerator, Optional
from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from core.bus import AgentEvent, EventBus
from core.cognitive_router import ModelRouter
from core.orchestrator import Orchestrator
from core.sandbox import SecuritySandbox
from core.schemas import ApprovalDecision, CreateRunRequest


def create_app(
    bus: Optional[EventBus] = None,
    router: Optional[ModelRouter] = None,
    sandbox: Optional[SecuritySandbox] = None,
) -> FastAPI:
    app = FastAPI(title="E-ZzIO Control Plane", version="1.0.0")
    event_bus = bus or EventBus()
    model_router = router or ModelRouter()
    security_sandbox = sandbox or SecuritySandbox()
    orchestrator = Orchestrator(bus=event_bus, router=model_router, sandbox=security_sandbox)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/api/runs")
    async def create_run(req: CreateRunRequest, bg: BackgroundTasks) -> dict[str, str]:
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        event_bus.register_run(run_id, prompt=req.prompt, profile=req.profile)
        bg.add_task(orchestrator.run, run_id, req.prompt, req.profile)
        return {"run_id": run_id, "status": "queued"}

    @app.get("/api/runs/{run_id}/stream")
    async def stream_events(run_id: str) -> StreamingResponse:
        queue = event_bus.subscribe(run_id)

        async def sse_generator() -> AsyncGenerator[str, None]:
            seen_ids: set[int] = set()
            try:
                past_events = event_bus.get_run_events(run_id)
                for pe in past_events:
                    event_id = pe["id"]
                    seen_ids.add(event_id)
                    yield f"data: {json.dumps(pe, ensure_ascii=False)}\n\n"
                    if pe["event_type"] == "final":
                        return

                while True:
                    try:
                        event: AgentEvent = await asyncio.wait_for(queue.get(), timeout=10.0)
                        if event.event_id and event.event_id in seen_ids:
                            continue
                        if event.event_id:
                            seen_ids.add(event.event_id)

                        data = {
                            "id": event.event_id,
                            "run_id": event.run_id,
                            "event_type": event.event_type,
                            "agent_id": event.agent_id,
                            "payload": event.payload,
                            "requires_approval": event.requires_approval,
                            "created_at": event.created_at,
                        }
                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                        if event.event_type == "final":
                            break
                    except asyncio.TimeoutError:
                        yield ": ping\n\n"
            finally:
                event_bus.unsubscribe(run_id, queue)

        return StreamingResponse(sse_generator(), media_type="text/event-stream")

    return app
