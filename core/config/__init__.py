"""E-ZZIO — configuration centrale (dont chargeur de secrets)."""
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
]
