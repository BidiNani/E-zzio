"""
Connecteurs applicatifs externes pour E-ZzIO (Discord, Webhooks, CI/CD).
"""

from .discord_bot import EzzioDiscordBot, create_ezzio_bot

__all__ = ["EzzioDiscordBot", "create_ezzio_bot"]
