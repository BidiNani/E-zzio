# core/integrations/discord/discord_client.py
from __future__ import annotations
import time
import logging
import httpx
import discord
from discord.ext import commands

from core.config.secrets_loader import load as load_secrets
from core.integrations.discord.ui_components import format_ezzio_response

logger = logging.getLogger("ezzio.discord")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Points d'accès gouvernés requis : /master/chat et /v1/chat/completions
MASTER_CHAT_URL = "http://127.0.0.1:8000/master/chat"
COMPLETIONS_URL = "http://127.0.0.1:8000/v1/chat/completions"

async def _handle_message(message: discord.Message):
    clean_content = message.content.replace(f"<@{bot.user.id}>", "").strip()
    if not clean_content:
        clean_content = "Salut"

    t0 = time.perf_counter()
    status = "SUCCESS"
    reply = ""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                MASTER_CHAT_URL,
                json={"message": clean_content, "stream": False}
            )
            if resp.status_code == 200:
                data = resp.json()
                reply = data.get("response", data.get("content", ""))
            else:
                status = "ERROR"
                reply = f"Erreur passerelle ({resp.status_code})"
    except Exception as e:
        logger.error(f"[DISCORD ROUTING ERROR] {e}")
        status = "ERROR"
        reply = f"Erreur noyau : {e}"

    latency_ms = (time.perf_counter() - t0) * 1000

    formatted = format_ezzio_response(
        content=reply,
        provider="master-kernel",
        model="native-fast",
        latency_ms=latency_ms,
        status=status
    )
    await message.reply(formatted, mention_author=False)

@bot.event
async def on_message(message: discord.Message):
    if getattr(message.author, "bot", False):
        return

    # process_commands(message)
    # await bot.process_commands(message)

    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        async with message.channel.typing():
            await _handle_message(message)
