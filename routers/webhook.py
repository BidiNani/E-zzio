import json
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel

from routers.chat import _core

logger = logging.getLogger("ezzio.api.webhook")
router = APIRouter(prefix="/api/v1/webhook", tags=["Webhook"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

EXPECTED_KEY = os.getenv("EZZIO_API_KEY", "ezzio_secret_key_local_dev")
MAX_PAYLOAD_SIZE = int(os.getenv("EZZIO_MAX_PAYLOAD_SIZE", 10 * 1024 * 1024))
MAX_FILES = int(os.getenv("EZZIO_MAX_FILES", 100))
MAX_TOKENS_ESTIMATE = int(os.getenv("EZZIO_MAX_TOKENS_ESTIMATE", 50000))

RATE_LIMIT_DB = Path("runtime/state/rate_limit.db")
RATE_LIMIT_DB.parent.mkdir(parents=True, exist_ok=True)


def init_rate_limit_db() -> None:
    try:
        with sqlite3.connect(RATE_LIMIT_DB, timeout=5.0) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_ip TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rate_ip_time ON requests(client_ip, timestamp);")
            conn.commit()
    except Exception as e:
        logger.error("DB Init Error: %s", e)


init_rate_limit_db()


def check_rate_limit(client_ip: str, max_requests: int = 10, window_sec: float = 60.0) -> bool:
    now = time.time()
    try:
        with sqlite3.connect(RATE_LIMIT_DB, timeout=5.0) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM requests WHERE client_ip = ? AND timestamp > ?",
                (client_ip, now - window_sec),
            )
            if cursor.fetchone()[0] >= max_requests:
                return False
            cursor.execute("INSERT INTO requests (client_ip, timestamp) VALUES (?, ?)", (client_ip, now))
            cursor.execute("DELETE FROM requests WHERE timestamp < ?", (now - 600.0,))
            conn.commit()
            return True
    except Exception:
        return True


class WebhookResponse(BaseModel):
    status: str = "success"
    response: str
    intent: str
    session_id: str


@router.post("/n8n", response_model=WebhookResponse)
async def n8n_webhook_receiver(request: Request, api_key: str = Depends(api_key_header)):
    forwarded_for = request.headers.get("X-Forwarded-For")
    client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else (request.client.host if request.client else "unknown")

    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    expected_key = os.getenv("EZZIO_API_KEY") or EXPECTED_KEY
    if not expected_key or api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    body_bytes = await request.body()
    if len(body_bytes) > MAX_PAYLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Payload too large")

    try:
        payload: dict[str, Any] = json.loads(body_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON") from None

    context_files: list[dict[str, Any]] = payload.get("context_files", [])
    if len(context_files) > MAX_FILES:
        raise HTTPException(status_code=400, detail="Too many files")

    message_str = str(payload.get("message") or payload.get("text") or payload.get("content") or "")
    context_chars = sum(len(str(f.get("snippet", ""))) for f in context_files)
    if (len(message_str) + context_chars) // 4 > MAX_TOKENS_ESTIMATE:
        raise HTTPException(status_code=400, detail="Too many tokens")

    user_id = payload.get("user_id", "webhook_user")
    session_id = payload.get("session_id", f"sess_{user_id}")

    # Fast-path pour les tests de connexion et de charge (n8n ping)
    if message_str == "test rate limit":
        return WebhookResponse(response="pong (rate limit test successful)", intent="ping", session_id=session_id)

    try:
        if not getattr(_core, "_is_initialized", False):
            await _core.init()
            _core._is_initialized = True

        res = await _core.think(user_id=user_id, message=message_str, session_id=session_id)
        return WebhookResponse(
            response=res.get("response", ""),
            intent=res.get("intent", "webhook"),
            session_id=res.get("session_id", session_id),
        )
    except Exception as e:
        logger.exception("Webhook internal error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e
