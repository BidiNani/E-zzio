import os
import discord
import aiohttp
from discord.ext import commands
from dotenv import load_dotenv
from pathlib import Path

# Chargement sécurisé
ENV_PATH = Path(__file__).parent.parent.parent / "secrets" / ".env"
load_dotenv(dotenv_path=ENV_PATH)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN or DISCORD_TOKEN == "ton_token_ici":
    raise ValueError(f"❌ ERREUR : DISCORD_TOKEN valide introuvable dans {ENV_PATH}")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def envoyer_au_cerveau(user_id: int, prompt: str) -> str:
    """Communique avec la Gateway FastAPI locale d'E-zzio."""
    url = "http://127.0.0.1:8000/master/chat"
    payload = {"user_id": str(user_id), "text": prompt, "speed": "auto"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=90) as response:
                if response.status != 200:
                    return f"❌ Erreur Serveur ({response.status})"
                result = await response.json()
                return result.get("response", "❌ Aucune réponse du cerveau.")
    except aiohttp.ClientConnectionError:
        return "🔌 **Erreur critique** : Le Cerveau Local (FastAPI) est éteint ou inaccessible."
    except Exception as e:
        return f"❌ Erreur inattendue : {str(e)}"

@bot.event
async def on_ready():
    print("==========================================")
    print(f"✅ [Discord Layer] Connecté en tant que : {bot.user}")
    print(f"📡 Prêt à router vers localhost:8000")
    print("==========================================")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    is_mention = bot.user in message.mentions
    is_dm = isinstance(message.channel, discord.DMChannel)
    is_named = "e-zzio" in message.content.lower() or "ezzio" in message.content.lower()

    if is_mention or is_dm or is_named:
        async with message.channel.typing():
            prompt = message.content.replace(f'<@{bot.user.id}>', '').strip() or "Système status ?"
            reponse = await envoyer_au_cerveau(message.author.id, prompt)
            
            reponse = reponse.strip() if reponse else "*(Silence radio du Cerveau)*"
            
            for i in range(0, len(reponse), 2000):
                await message.channel.send(reponse[i:i+2000])
    
    await bot.process_commands(message)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
