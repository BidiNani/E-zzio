import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from runtime.model_router import EzzioModelRouter, ModelRequest

router = APIRouter(prefix="/api/mobile", tags=["mobile"])
orchestrator = EzzioModelRouter()


@router.websocket("/ws")
async def mobile_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)

            req = ModelRequest(
                prompt=payload.get("prompt", ""),
                task=payload.get("task", "general"),
                complexity=payload.get("complexity", "low"),
                latency=payload.get("latency", "normal"),
                budget=payload.get("budget", "local_first"),
                system_prompt=payload.get("system_prompt"),
            )

            response = orchestrator.generate(req, agent_id="samsung_a33_client")

            await websocket.send_json(
                {
                    "ok": True,
                    "content": response.get("response", ""),
                    "model_used": response.get("model_used"),
                    "provider_used": response.get("provider_used"),
                    "latency_ms": response.get("latency_ms", 0),
                    "fallback_applied": False,
                }
            )
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"ok": False, "error": str(e)})
