"""
E-ZZIO Sovereign Discord Agent Client (V7.51 Dynamic Presence & Vault Hardened)
Intègre le Secure Vault, la session aiohttp persistante et le statut dynamique.
"""
import os
import sys
import pathlib
import discord
from discord.ext import commands, tasks
import aiohttp

PROJECT_ROOT = pathlib.Path(r"G:\AI\E-zzio")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.integrations.discord.permission_guard import permission_guard
from core.security.secret_redactor import secret_redactor
from core.integrations.discord.discord_watchdog import discord_watchdog
from core.tool_gateway.google_bridge import GoogleIdentityBridge
from runtime.adapters.config.dotenv_provider import DotEnvConfigProvider

config = DotEnvConfigProvider(env_path=str(PROJECT_ROOT / "secrets" / ".env"))
google_bridge = GoogleIdentityBridge(config=config)

OWNER_ID = "186035306418405376"

def resolve_discord_token() -> str:
    try:
        vault_res = google_bridge.retrieve_tokens()
        if vault_res.get("valid"):
            tokens = vault_res.get("tokens", {})
            if "discord_bot_token" in tokens:
                return tokens["discord_bot_token"]
    except Exception:
        pass
    return config.get("DISCORD_BOT_TOKEN") or config.get("DISCORD_TOKEN")

DISCORD_TOKEN = resolve_discord_token()
LOCAL_API_URL = config.get("EZZIO_LOCAL_API_URL", "http://127.0.0.1:8001/master/chat")

if not DISCORD_TOKEN:
    print("[!] ERREUR CRITIQUE : Aucun token Discord trouvé.")
    sys.exit(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!e ", intents=intents)

http_session: aiohttp.ClientSession = None

@tasks.loop(minutes=10)
async def update_dynamic_presence():
    """Met à jour périodiquement le statut du bot pour refléter la santé de l'infrastructure."""
    try:
        activity = discord.Activity(type=discord.ActivityType.watching, name="🧠 E-ZZIO | Kernel ONLINE | 🔐 Vault OK")
        await bot.change_presence(status=discord.Status.online, activity=activity)
    except Exception:
        pass

@bot.event
async def on_ready():
    global http_session
    if http_session is None or http_session.closed:
        http_session = aiohttp.ClientSession()
    
    if not update_dynamic_presence.is_running():
        update_dynamic_presence.start()
        
    print(f"[E-ZZIO SENSE] Agent Discord V7.51 en ligne : {bot.user}")
    print(f"[*] Canal d'orchestration persistant : {LOCAL_API_URL}")

@bot.event
async def on_close():
    global http_session
    if http_session and not http_session.closed:
        await http_session.close()

@bot.event
async def on_message(message):
    global http_session
    if message.author == bot.user:
        return
        
    discord_user_id = str(message.author.id)
    username = str(message.author.name)
    is_private = isinstance(message.channel, discord.DMChannel)
    guild_id = str(message.guild.id) if message.guild else None

    auth_check = permission_guard.evaluate_guild_access(guild_id, discord_user_id, username, is_private)
    if not auth_check["granted"]:
        if is_private:
            await message.channel.send("❌ Accès privé non autorisé.")
        return 

    if is_private:
        clean_prompt = message.content.strip()
    else:
        if not message.content.startswith("!e "):
            return
        clean_prompt = message.content[3:].strip()

    if not clean_prompt and not message.attachments:
        return
        
    discord_watchdog.record_activity()
    
    async with message.channel.typing():
        try:
            payload = {
                "user_id": discord_user_id,
                "username": username,
                "text": clean_prompt,
                "source": "discord_dm" if is_private else "discord_channel",
                "guild_id": guild_id,
                "autoriser_outils_locaux": True
            }
            
            if message.attachments:
                for attachment in message.attachments:
                    if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']):
                        payload["image_url"] = attachment.url
                        break 
            
            if http_session is None or http_session.closed:
                http_session = aiohttp.ClientSession()

            async with http_session.post(LOCAL_API_URL, json=payload, timeout=45.0) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    raw_res = data.get("response", "")
                    if isinstance(raw_res, dict):
                        reply_text = raw_res.get("response") or raw_res.get("answer") or raw_res.get("content") or str(raw_res)
                    elif isinstance(raw_res, str):
                        reply_text = raw_res
                    else:
                        reply_text = str(raw_res) if raw_res else "Réponse vide du noyau."

                else:
                    reply_text = f"Erreur de communication noyau (Code {resp.status})."
            
            chunk_size = 1950
            for i in range(0, len(reply_text), chunk_size):
                if is_private:
                    await message.channel.send(reply_text[i:i+chunk_size])
                else:
                    await message.reply(reply_text[i:i+chunk_size])
                
        except Exception as e:
            safe_error = secret_redactor.sanitize(str(e))
            error_reply = "❌ Erreur interne E-ZZIO."
            if is_private:
                await message.channel.send(error_reply)
            else:
                await message.reply(error_reply)
            
    await bot.process_commands(message)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
