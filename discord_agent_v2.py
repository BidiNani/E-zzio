# ==============================================================================
# E-ZZIO SOVEREIGN DISCORD AGENT v2 (OMNIPRESENT)
# ==============================================================================

import os
import sys
import pathlib
import discord
from discord.ext import commands
import aiohttp
from dotenv import load_dotenv

PROJECT_ROOT = pathlib.Path(r"G:\AI\E-zzio")
env_root = PROJECT_ROOT / "omnipresence.env"
env_secrets = PROJECT_ROOT / "secrets" / "omnipresence.env"

if env_root.exists():
    load_dotenv(dotenv_path=env_root, override=True)
elif env_secrets.exists():
    load_dotenv(dotenv_path=env_secrets, override=True)
else:
    load_dotenv(PROJECT_ROOT / "secrets" / ".env", override=True)

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
LOCAL_API_URL = "http://127.0.0.1:8001/master/chat"

if not DISCORD_TOKEN:
    print("[!] ERREUR CRITIQUE : Aucun token Discord trouvé.")
    sys.exit(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!e ", intents=intents)

@bot.event
async def on_ready():
    print(f"[E-ZZIO SENSE] Agent Discord en ligne (Omniprésent) : {bot.user}")
    print(f"[*] Connecté au noyau local sur : {LOCAL_API_URL}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
        
    clean_prompt = message.content.strip()
    if not clean_prompt and not message.attachments:
        return
        
    async with message.channel.typing():
        try:
            payload = {
                "user_id": str(message.author.name),
                "text": clean_prompt,
                "autoriser_outils_locaux": True
            }
            
            if message.attachments:
                for attachment in message.attachments:
                    if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']):
                        payload["image_url"] = attachment.url
                        break 
            
            async with aiohttp.ClientSession() as session:
                async with session.post(LOCAL_API_URL, json=payload, timeout=45.0) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        reply_text = data.get("response", "Réponse vide du noyau.")
                    else:
                        reply_text = f"Erreur de communication noyau (Code {resp.status})."
            
            chunk_size = 1950
            for i in range(0, len(reply_text), chunk_size):
                await message.reply(reply_text[i:i+chunk_size])
                
        except Exception as e:
            await message.reply(f"❌ Erreur critique d'orchestration : `{e}`")
            
    await bot.process_commands(message)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)