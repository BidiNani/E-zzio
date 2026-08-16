import os
import discord
from discord.ext import commands
from discord import app_commands
import httpx
from core.secrets import load_secrets

class ChatCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        load_secrets()
        api_port = os.getenv("EZZIO_API_PORT", "8001")
        self.api_url = f"http://127.0.0.1:{api_port}/api/v1/chat"

    @app_commands.command(name="chat", description="Dialogue naturel avec l'agent autonome E-ZZIO")
    @app_commands.describe(message="Votre message, question ou directive")
    async def chat_slash(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(thinking=True)
        user_id = str(interaction.user.id)
        channel_id = str(interaction.channel_id)

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                payload = {
                    "message": message,
                    "user_id": user_id,
                    "session_id": f"discord_{channel_id}"
                }
                resp = await client.post(self.api_url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            reply = data.get("response", "Aucune réponse générée.")
            provider = data.get("provider", "unknown").upper()
            intent = data.get("intent", "chat").upper()

            embed = discord.Embed(description=reply[:4000], color=discord.Color.teal())
            embed.set_footer(text=f"E-ZZIO Autonomous | Intent: {intent} | Provider: {provider}")
            await interaction.followup.send(embed=embed)

        except Exception as exc:
            await interaction.followup.send(f"❌ **Erreur d'orchestration :** {str(exc)}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Réponse automatique sur mention du bot
        if self.bot.user in message.mentions:
            clean_content = message.content.replace(f"<@{self.bot.user.id}>", "").strip()
            if not clean_content:
                return

            async with message.channel.typing():
                try:
                    async with httpx.AsyncClient(timeout=90.0) as client:
                        payload = {
                            "message": clean_content,
                            "user_id": str(message.author.id),
                            "session_id": f"discord_{message.channel.id}"
                        }
                        resp = await client.post(self.api_url, json=payload)
                        resp.raise_for_status()
                        data = resp.json()

                    reply = data.get("response", "Aucune réponse.")
                    provider = data.get("provider", "unknown").upper()
                    intent = data.get("intent", "chat").upper()

                    embed = discord.Embed(description=reply[:4000], color=discord.Color.teal())
                    embed.set_footer(text=f"E-ZZIO Autonomous | Intent: {intent} | Provider: {provider}")
                    await message.reply(embed=embed)

                except Exception as exc:
                    await message.reply(f"❌ **Erreur :** {str(exc)}")

async def setup(bot: commands.Bot):
    await bot.add_cog(ChatCog(bot))
