"""
[DEPRECATED] Ce fichier importe un module runtime.* supprime (archive 2026-09-18).
A migrer ou supprimer. Ne pas utiliser en production.
"""

from pathlib import Path

ROOT = Path(r"G:\AI\E-zzio")
ROUTERS_DIR = ROOT / "runtime" / "routers"
ROUTERS_DIR.mkdir(parents=True, exist_ok=True)

mobile_router_code = """import json
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
                system_prompt=payload.get("system_prompt")
            )

            response = orchestrator.generate(req, agent_id="samsung_a33_client")

            await websocket.send_json({
                "ok": True,
                "content": response.content,
                "model_used": response.model_used,
                "provider_used": response.provider_used,
                "latency_ms": response.latency_ms,
                "fallback_applied": response.fallback_applied
            })
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"ok": False, "error": str(e)})
"""

(ROUTERS_DIR / "mobile.py").write_text(mobile_router_code, encoding="utf-8")
print("[OK] Passerelle WebSocket runtime/routers/mobile.py déployée.")
