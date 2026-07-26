import os
import discord
import aiohttp
from discord.ext import commands
from dotenv import load_dotenv
from pathlib import Path

ENV_PATH = Path(__file__).parent / "secrets" / ".env"
load_dotenv(dotenv_path=ENV_PATH)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError(f"❌ ERREUR : DISCORD_TOKEN introuvable dans {ENV_PATH}")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def envoyer_au_cerveau(user_id, prompt):
    url = "http://127.0.0.1:8000/master/chat"
    payload = {"user_id": str(user_id), "text": prompt, "speed": "auto"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=90) as response:
                result = await response.json()
                if "error" in result:
                    return f"❌ Erreur du Cerveau : {result['error']}"
                return result.get("response", "")
    except Exception as e:
        return f"❌ Erreur de connexion au Cerveau FastAPI : {str(e)}"

@bot.event
async def on_ready():
    print("==========================================")
    print(f"✅ [Discord] Bot en ligne : {bot.user}")
    print("🔗 Connecté au Cerveau FastAPI Local")
    print("==========================================")

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    
    # CORRECTIF 1 : Détection intelligente (Mention OU MP OU Nom prononcé)
    is_mention = bot.user in message.mentions
    is_dm = isinstance(message.channel, discord.DMChannel)
    is_named = "e-zzio" in message.content.lower() or "ezzio" in message.content.lower()

    if is_mention or is_dm or is_named:
        async with message.channel.typing():
            prompt = message.content.replace(f'<@{bot.user.id}>', '').strip() or "Es-tu là ?"
            reponse = await envoyer_au_cerveau(message.author.id, prompt)
            
            # CORRECTIF 2 : Sécurité anti-message vide
            reponse = reponse.strip() if reponse else ""
            if not reponse:
                reponse = "*(Ma réflexion a planté ou a été coupée. Tu peux reformuler ?)*"
            
            for i in range(0, len(reponse), 2000):
                await message.channel.send(reponse[i:i+2000])
    
    await bot.process_commands(message)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)