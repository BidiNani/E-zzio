import asyncio
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
import discord
from discord.ext import commands

sys.path.insert(0, os.getcwd())

from core.secrets import load_secrets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ezzio.discord")

# 1. Chargement standardisé + fallback direct sur secrets/.env et .env
load_secrets()
env_path = Path("secrets/.env")
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
load_dotenv(dotenv_path=".env", override=False)

TOKEN = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")

if not TOKEN:
    logger.error("Aucun token Discord trouvé (vérifie DISCORD_BOT_TOKEN ou DISCORD_TOKEN dans secrets/.env).")
    sys.exit(1)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info(f"Connecté en tant que {bot.user} (ID: {bot.user.id})")
    try:
        # Chargement des Cogs
        await bot.load_extension("runtime.discord.cogs.chat")
        await bot.load_extension("runtime.discord.cogs.research")
        
        # Synchronisation globale de l'arbre slash commands (/chat, /research, /recall)
        synced = await bot.tree.sync()
        logger.info(f"[OK] Arbre synchronisé : {len(synced)} commande(s) active(s) -> {[c.name for c in synced]}")
    except Exception as e:
        logger.error(f"[ERREUR] Échec chargement/sync : {e}", exc_info=True)

async def main():
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
