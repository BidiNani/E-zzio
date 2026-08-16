import sys
import os
from pathlib import Path

# Résolution garantie de la racine du projet quel que soit le dossier de lancement
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import asyncio
import discord
from discord.ext import commands
from core.secrets import load_secrets

load_secrets()
token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")

if not token:
    raise RuntimeError("DISCORD_BOT_TOKEN absent de secrets/.env ou variables d'environnement")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print("==================================================")
    print(f"[OK] Bot Discord connecté : {bot.user.name} (ID: {bot.user.id})")
    print("[*] Chargement dynamique des cogs...")
    
    cogs_dir = ROOT_DIR / "runtime" / "discord" / "cogs"
    if cogs_dir.exists():
        for file in cogs_dir.glob("*.py"):
            if not file.name.startswith("__"):
                extension_name = f"runtime.discord.cogs.{file.stem}"
                try:
                    await bot.load_extension(extension_name)
                    print(f"     [+] Cog chargé : {file.stem}")
                except Exception as e:
                    print(f"     [-] Erreur sur {file.stem} : {e}")

    # Synchronisation des commandes slash
    print("[*] Synchronisation de l'arbre des commandes slash (/)...")
    try:
        synced = await bot.tree.sync()
        print(f"[OK] {len(synced)} commande(s) slash enregistrée(s) :")
        for cmd in synced:
            print(f"     - /{cmd.name} : {cmd.description}")
    except Exception as e:
        print(f"[ERREUR] Échec de la synchronisation slash : {e}")
        
    print("==================================================")

async def main():
    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
