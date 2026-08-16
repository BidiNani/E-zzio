import os
import discord
from discord.ext import commands
from discord import app_commands
import httpx
from core.secrets import load_secrets

class ResearchCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        load_secrets()
        api_port = os.getenv("EZZIO_API_PORT", "8001")
        self.api_url = f"http://127.0.0.1:{api_port}/api/v1/research/search"

    @app_commands.command(name="research", description="Recherche hybride gouvernée multi-fournisseurs")
    @app_commands.describe(
        query="Requête de recherche ou d'investigation",
        mode="Mode de recherche (fast, research, google, local, forensic)"
    )
    @app_commands.choices(mode=[
        app_commands.Choice(name="Fast (Tavily)", value="fast"),
        app_commands.Choice(name="Research (Jina + Tavily)", value="research"),
        app_commands.Choice(name="Google (Gemini 3.7)", value="google"),
        app_commands.Choice(name="Local (Qwen 3.5)", value="local"),
        app_commands.Choice(name="Forensic (SearXNG + Jina)", value="forensic")
    ])
    async def research_slash(self, interaction: discord.Interaction, query: str, mode: str = "fast"):
        await interaction.response.defer(thinking=True)
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                payload = {"query": query, "mode": mode, "task_id": f"disc_{interaction.id}"}
                resp = await client.post(self.api_url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            provider = data.get("provider", "unknown").upper()
            embed = discord.Embed(title=f"🔎 Investigation ({mode.upper()})", description=f"**Requête :** {query}", color=discord.Color.blue())
            
            results = data.get("data", {}).get("results", [])
            text_response = data.get("data", {}).get("text", "")
            
            if text_response:
                embed.add_field(name="Synthèse", value=text_response[:1024], inline=False)
            elif results:
                for idx, item in enumerate(results[:3], 1):
                    embed.add_field(
                        name=f"{idx}. {item.get('title', 'Lien')[:100]}",
                        value=f"[Consulter la source]({item.get('url')})\n{item.get('content', '')[:180]}...",
                        inline=False
                    )
            
            embed.set_footer(text=f"E-ZZIO Research | Moteur: {provider} | Task ID: {data.get('task_id')}")
            await interaction.followup.send(embed=embed)
        except Exception as exc:
            await interaction.followup.send(f"❌ **Erreur d'investigation :** {str(exc)}")

async def setup(bot: commands.Bot):
    await bot.add_cog(ResearchCog(bot))
