"""
core/config.py — Configuration centralisée E-zzio.

Mode d'exécution :
  - local   : 127.0.0.1 uniquement, pas d'auth, tout autorisé
  - lan     : 0.0.0.0, CORS restreint, code d'accès simple (famille)
  - private : idem lan + JWT + isolation
  - public  : idem private + HTTPS + rate limit strict
"""
from __future__ import annotations

import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

# Mode d'exécution
EZZIO_MODE = os.environ.get("EZZIO_MODE", "lan").lower()

# Ports
BACKEND_PORT = int(os.environ.get("EZZIO_BACKEND_PORT", "8001"))
FRONTEND_PORT = int(os.environ.get("EZZIO_FRONTEND_PORT", "1420"))

# IP LAN (détectée au démarrage par start-ezzio.ps1, sinon valeur par défaut)
LAN_IP = os.environ.get("EZZIO_LAN_IP", "192.168.1.10")

# Host de bind
if EZZIO_MODE == "local":
    HOST = "127.0.0.1"
else:
    HOST = "0.0.0.0"

# CORS
if EZZIO_MODE == "local":
    ALLOWED_ORIGINS = ["*"]
else:
    ALLOWED_ORIGINS = [
        f"http://localhost:{FRONTEND_PORT}",
        f"http://127.0.0.1:{FRONTEND_PORT}",
        f"http://{LAN_IP}:{FRONTEND_PORT}",
        "tauri://localhost",
        "http://tauri.localhost",
    ]

# Auth
REQUIRE_AUTH = EZZIO_MODE in ("lan", "private", "public")
ACCESS_CODE = os.environ.get("EZZIO_ACCESS_CODE", "")  # généré au 1er lancement

# Rate limit
if EZZIO_MODE == "local":
    RATE_LIMIT = "300/minute"
elif EZZIO_MODE == "lan":
    RATE_LIMIT = "120/minute"
elif EZZIO_MODE == "private":
    RATE_LIMIT = "60/minute"
else:
    RATE_LIMIT = "30/minute"

# Erreurs
MASK_ERRORS = EZZIO_MODE in ("private", "public")

# Logs
LOG_JSON = EZZIO_MODE in ("lan", "private", "public")
# ============================================================
# AJOUTS B2-SECURITY — rate limit + sécurité body
# ============================================================
# Rate limit par IP (requêtes par minute). Utilisé par Guardian.
RATE_LIMIT_PER_MIN = 120

# Taille max du body en octets (anti-DoS payload)
MAX_BODY_BYTES = 1 * 1024 * 1024   # 1 MiB

# Timeout d'une requête en secondes
REQUEST_TIMEOUT_S = 30

# Chemins exclus du rate limit (santé, métriques)
RATE_LIMIT_EXEMPT_PATHS = ["/health", "/favicon.ico"]

# Origines autorisées pour les requêtes cross-origin (CORS strict)
# Si vide, on garde ALLOWED_ORIGINS de la config existante
CORS_STRICT_BLOCK = True   # True = 403 si Origin absent de ALLOWED_ORIGINS

