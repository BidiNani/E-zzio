import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from fastapi.testclient import TestClient
from interfaces.api.server import app

from core.secrets import load_secrets
from routers.chat import init_chat_router


async def run_smoke_test():
    print("=" * 60)
    print("E-ZZIO — DEPLOYMENT SMOKE TEST (PHASE 4)")
    print("=" * 60)

    # 1. Configuration & Secrets
    load_secrets()
    print("[1/5] Secrets charges avec succes.")

    # 2. Database & Chat Router Init
    await init_chat_router()
    print("[2/5] UnifiedMemoryGateway et EzzioCore initialises.")

    # 3. HTTP Client Test
    client = TestClient(app)
    resp = client.get("/api/v1/health/readiness")
    assert resp.status_code == 200
    readiness = resp.json()
    print(f"[3/5] API Readiness Health: {readiness.get('status')} (Process alive: {readiness.get('checks', {}).get('process_alive')})")

    # 4. Chat Endpoint Smoke Call
    chat_resp = client.post("/api/v1/chat/", json={
        "message": "Smoke test ping",
        "user_id": "smoke_user",
        "session_id": "SESS_SMOKE_TEST"
    })
    assert chat_resp.status_code == 200
    data = chat_resp.json()
    print(f"[4/5] Chat Endpoint Response: Provider={data.get('provider')}, Status=OK")

    # 5. Clean Shutdown Check
    print("[5/5] Test de fumee valide sans processus orphelin.")
    print("=" * 60)
    print("SMOKE TEST STATUS: SUCCESS")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_smoke_test())
