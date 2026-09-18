"""
core/security/guardian.py — Middleware de sécurité E-ZZIO.

Applique dans l'ordre :
1. Correlation ID (propagé ou généré)
2. Rate limit par IP (120 req/min, exclusions /health)
3. CORS strict (403 si Origin non autorisée)
4. Headers de sécurité (nosniff, DENY, no-referrer)
5. Télémétrie (x-guardian-duration-ms)

Mode :
  local   : CORS strict désactivé (127.0.0.1 uniquement)
  lan     : CORS strict actif, rate limit actif
  private : idem lan + auth JWT (à venir)
  public  : idem private + HTTPS forcé
"""
from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.app_config import (
    ALLOWED_ORIGINS,
    CORS_STRICT_BLOCK,
    EZZIO_MODE,
    MAX_BODY_BYTES,
    RATE_LIMIT_EXEMPT_PATHS,
    RATE_LIMIT_PER_MIN,
)

log = logging.getLogger("Guardian")


# ============================================================
# Rate limiter en mémoire — fenêtre glissante par IP
# ============================================================
class RateLimiter:
    """Sliding window par IP. Thread-safe via GIL (acceptable en mono-process)."""

    def __init__(self, max_requests: int, window_s: int = 60):
        self.max = max_requests
        self.window_s = window_s
        self._hits: dict[str, deque] = defaultdict(deque)

    def check(self, ip: str) -> tuple[bool, int, int]:
        """Retourne (autorisé, restant, retry_after_s)."""
        now = time.monotonic()
        cutoff = now - self.window_s
        q = self._hits[ip]

        # Purge des hits trop vieux
        while q and q[0] < cutoff:
            q.popleft()

        if len(q) >= self.max:
            retry_after = int(q[0] + self.window_s - now) + 1
            return False, 0, retry_after

        q.append(now)
        return True, self.max - len(q), 0


# ============================================================
# Middleware principal
# ============================================================
class GuardianMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, cors_origins: list[str], strict_cors: bool):
        super().__init__(app)
        self.cors_origins = set(cors_origins)
        self.strict_cors = strict_cors
        self.rate_limiter = RateLimiter(RATE_LIMIT_PER_MIN, 60)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        t0 = time.perf_counter()

        # --- 0. PRÉFLIGHT CORS OPTIONS (navigateur) — réponse immédiate
        if request.method == "OPTIONS":
            origin = request.headers.get("origin", "")
            if origin and origin in self.cors_origins:
                resp = Response(status_code=200)
                resp.headers["Access-Control-Allow-Origin"] = origin
                resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
                resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Correlation-ID, X-Requested-With, X-API-Key"
                resp.headers["Access-Control-Allow-Credentials"] = "true"
                resp.headers["Access-Control-Max-Age"] = "86400"
                resp.headers["Vary"] = "Origin"
                return resp

        # --- 1. Correlation ID (propagé ou généré)
        cid = request.headers.get("x-correlation-id") or f"req_{uuid.uuid4().hex[:12]}"

        # --- 2. Rate limit (par IP réelle)
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        if not any(path == exempt or path.startswith(exempt) for exempt in RATE_LIMIT_EXEMPT_PATHS):
            # [B2-FIX2] log temporaire pour debug rate limit
            log.info(f"[GUARDIAN][HIT] ip={client_ip} path={path}")
            allowed, remaining, retry_after = self.rate_limiter.check(client_ip)
            if not allowed:
                dur_ms = round((time.perf_counter() - t0) * 1000, 2)
                log.warning(f"[GUARDIAN][RATE] 429 {client_ip} {path} (retry={retry_after}s)")
                resp = JSONResponse(
                    status_code=429,
                    content={"error": "rate_limit_exceeded", "retry_after": retry_after},
                )
                self._apply_headers(resp, cid, dur_ms)
                resp.headers["Retry-After"] = str(retry_after)
                resp.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_PER_MIN)
                resp.headers["X-RateLimit-Remaining"] = "0"
                return resp

        # --- 3. CORS strict
        origin = request.headers.get("origin")
        if self.strict_cors and origin:
            if origin not in self.cors_origins:
                dur_ms = round((time.perf_counter() - t0) * 1000, 2)
                log.warning(f"[GUARDIAN] 403 CORS denied origin={origin} path={path}")
                resp = JSONResponse(
                    status_code=403,
                    content={"error": "cors_origin_not_allowed", "origin": origin},
                )
                self._apply_headers(resp, cid, dur_ms)
                return resp

        # --- 4. Body size check (Content-Length uniquement, sans lire le body)
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > MAX_BODY_BYTES:
            dur_ms = round((time.perf_counter() - t0) * 1000, 2)
            log.warning(f"[GUARDIAN] 413 payload too large {cl} > {MAX_BODY_BYTES}")
            resp = JSONResponse(
                status_code=413,
                content={"error": "payload_too_large", "max": MAX_BODY_BYTES},
            )
            self._apply_headers(resp, cid, dur_ms)
            return resp

        # --- 5. Appel des routes
        try:
            response = await call_next(request)
        except Exception as e:
            dur_ms = round((time.perf_counter() - t0) * 1000, 2)
            log.exception(f"[GUARDIAN] 500 unhandled path={path}: {e}")
            resp = JSONResponse(
                status_code=500,
                content={"error": "internal_error", "correlation_id": cid},
            )
            self._apply_headers(resp, cid, dur_ms)
            return resp

        # --- 6. Headers CORS si origine autorisée
        if origin and origin in self.cors_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Correlation-ID, X-API-Key"
            response.headers["Vary"] = "Origin"

        # --- 7. Headers sécurité + télémétrie
        dur_ms = round((time.perf_counter() - t0) * 1000, 2)
        self._apply_headers(response, cid, dur_ms)

        return response

    @staticmethod
    def _apply_headers(resp: Response, cid: str, dur_ms: float) -> None:
        resp.headers["X-Correlation-ID"] = cid
        resp.headers["X-Guardian-Mode"] = EZZIO_MODE
        resp.headers["X-Guardian-Duration-Ms"] = str(dur_ms)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"


# ============================================================
# Point d'entrée
# ============================================================
def setup_guardian(app: FastAPI) -> None:
    """Installe le middleware Guardian sur l'app FastAPI."""
    strict = CORS_STRICT_BLOCK and EZZIO_MODE in ("lan", "private", "public")

    app.add_middleware(
        GuardianMiddleware,
        cors_origins=list(ALLOWED_ORIGINS),
        strict_cors=strict,
    )

    log.info(f"[GUARDIAN] Mode          : {EZZIO_MODE}")
    log.info(f"[GUARDIAN] CORS strict   : {strict}")
    log.info(f"[GUARDIAN] CORS origines : {len(ALLOWED_ORIGINS)}")
    log.info(f"[GUARDIAN] Rate limit    : {RATE_LIMIT_PER_MIN}/min par IP")
    log.info(f"[GUARDIAN] Body max      : {MAX_BODY_BYTES} octets")
    log.info("[GUARDIAN] Prêt")

