"""E-ZZIO — configuration centrale (dont chargeur de secrets) + config LAN."""
# ============================================================
# Configuration LAN / Mode (ex-core/config.py)
# ============================================================
from core.app_config import (
    ACCESS_CODE,
    ALLOWED_ORIGINS,
    BACKEND_PORT,
    EZZIO_MODE,
    FRONTEND_PORT,
    HOST,
    LAN_IP,
    LOG_JSON,
    MASK_ERRORS,
    RATE_LIMIT,
    REQUIRE_AUTH,
)
from core.config.secrets_loader import (
    discord_owner_id,
    discord_token,
    gemini_keys,
    groq_key,
    load,
    log_secrets_diagnostics,
)

__all__ = [
    "load",
    "discord_token",
    "discord_owner_id",
    "groq_key",
    "gemini_keys",
    "log_secrets_diagnostics",
    # Nouveaux
    "EZZIO_MODE",
    "HOST",
    "LAN_IP",
    "BACKEND_PORT",
    "FRONTEND_PORT",
    "ALLOWED_ORIGINS",
    "REQUIRE_AUTH",
    "ACCESS_CODE",
    "RATE_LIMIT",
    "MASK_ERRORS",
    "LOG_JSON",
]
