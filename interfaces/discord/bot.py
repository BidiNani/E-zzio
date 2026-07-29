import os
import discord
import asyncio
import sys
import aiohttp
from discord.ext import commands
from dotenv import load_dotenv
from pathlib import Path

ENV_PATH = Path(__file__).parent.parent.parent / "secrets" / ".env"
load_dotenv(dotenv_path=ENV_PATH)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GATEWAY_SECRET = os.getenv("EZZIO_GATEWAY_SECRET", "ezzio-local-secure-token-2026")
API_BASE_URL = "http://127.0.0.1:8001"

if not DISCORD_TOKEN or DISCORD_TOKEN == "ton_token_ici":
    print("⚠️ Avertissement : DISCORD_TOKEN non configuré. Le bot ne pourra pas se connecter.")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_headers():
    return {"Authorization": f"Bearer {GATEWAY_SECRET}"}

async def interroger_api(endpoint: str, payload: dict = None) -> dict:
    url = f"{API_BASE_URL}{endpoint}"
    try:
        async with aiohttp.ClientSession(headers=get_headers()) as session:
            if payload:
                async with session.post(url, json=payload, timeout=90) as response:
                    return await response.json()
            else:
                async with session.get(url, timeout=10) as response:
                    return await response.json()
    except Exception as e:
        return {"error": str(e)}

@bot.command(name="status")
async def system_status(ctx):
    """Commande système : interroge l'état de la Gateway E-zzio."""
    result = await interroger_api("/health")
    if "error" in result:
        await ctx.send(f"❌ **Erreur Gateway** : Impossible de joindre le cerveau local (`{result['error']}`).")
        return
    
    msg = (
        f"🧠 **E-ZZIO KERNEL STATUS**\n"
        f"**Core:** `{result.get('status', 'UNKNOWN')}`\n"
        f"**Runtime:** `{result.get('runtime', 'UNKNOWN')}`\n"
        f"**Memory:** `{result.get('memory', 'UNKNOWN')}`\n"
        f"**Recovery Guard:** `{result.get('recovery', 'UNKNOWN')}`\n"
        f"**Hardware Mode:** `{result.get('hardware_mode', 'UNKNOWN')}`"
    )
    await ctx.send(msg)

@bot.event
async def on_ready():
    print(f"✅ [Discord Layer] Bot en ligne : {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    
    await bot.process_commands(message)
    
    if message.content.startswith("!"): return # Ignoré car géré par les commandes

    is_mention = bot.user in message.mentions
    is_dm = isinstance(message.channel, discord.DMChannel)
    is_named = "e-zzio" in message.content.lower() or "ezzio" in message.content.lower()

    if is_mention or is_dm or is_named:
        async with message.channel.typing():
            prompt = message.content.replace(f'<@{bot.user.id}>', '').strip() or "Système status ?"
            payload = {"user_id": str(message.author.id), "text": prompt, "speed": "auto"}
            
            result = await interroger_api("/master/chat", payload)
            reponse = result.get("response") if "error" not in result else f"❌ Erreur API : {result['error']}"
            
            for i in range(0, len(reponse), 2000):
                await message.channel.send(reponse[i:i+2000])



# ============================================================
# E-ZZIO AUTONOMOUS GOVERNOR BRIDGE
# ============================================================
ROOT_PATH = Path(__file__).parent.parent.parent
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

try:
    from runtime.governor.gemini_bridge import autonomous_agent
    HAS_GOVERNOR = True
except ImportError as e:
    print(f"⚠️ Erreur import Governor : {e}")
    HAS_GOVERNOR = False

@bot.command(name="auto")
async def autonomous_task(ctx, *, prompt: str):
    """Délègue une tâche de code ou système au Governor Autonome."""
    if not HAS_GOVERNOR:
        await ctx.send("❌ Governor hors ligne ou module introuvable.")
        return
        
    msg = await ctx.send("⚙️ **E-ZZIO Governor** analyse et agit (cela peut prendre quelques secondes/minutes)...")
    
    try:
        # Exécution dans un thread séparé pour ne pas bloquer l'Event Loop asynchrone de Discord
        reponse = await asyncio.to_thread(autonomous_agent.run_task, prompt)
        
        if not reponse:
            reponse = "⚠️ Tâche terminée, mais aucune réponse textuelle renvoyée."
            
        # Fragmentation sécurisée pour la limite Discord des 2000 caractères
        for i in range(0, len(reponse), 2000):
            chunk = reponse[i:i+2000]
            if i == 0:
                await msg.edit(content=chunk)
            else:
                await ctx.send(chunk)
    except Exception as e:
        await msg.edit(content=f"❌ **Erreur Critique Governor** : {str(e)}")
# ============================================================

if __name__ == "__main__":
    if DISCORD_TOKEN and DISCORD_TOKEN != "ton_token_ici":
        bot.run(DISCORD_TOKEN)
    else:
        print("❌ ERREUR FATALE : DISCORD_TOKEN invalide ou non configuré dans secrets/.env")

