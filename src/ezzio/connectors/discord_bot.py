"""
Connecteur Discord Bot / Cog pour E-ZzIO.
Connecte les messages Discord au graphe d'orchestration LangGraph avec persistance de canal par thread_id.
"""

import logging
from typing import Any
import discord
from discord.ext import commands

from ezzio.graph.workflow import app as graph_app
from ezzio.tools.system_tools import check_ollama_health
from ezzio.self_repair.auto_healer import AutoHealer

logger = logging.getLogger("EzzioDiscord")


class EzzioCog(commands.Cog, name="EzzioCore"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="ez", help="Poser une question ou donner un ordre à E-ZzIO")
    async def ask_ezzio(self, ctx: commands.Context, *, query: str):
        async with ctx.typing():
            thread_id = f"discord_{ctx.channel.id}"
            initial_state = {
                "query": query,
                "thread_id": thread_id,
                "route": "direct",
                "answer": "",
                "sources": [],
                "model_used": "",
            }
            config = {"configurable": {"thread_id": thread_id}}
            
            try:
                final_state = await graph_app.ainvoke(initial_state, config=config)
                answer = final_state.get("answer", "Aucune réponse générée.")
                model = final_state.get("model_used", "E-ZzIO")
                route = final_state.get("route", "direct")
                
                header = f"**[E-ZzIO | Route: {route.upper()} | Modèle: {model}]**\n\n"
                full_response = header + answer
                
                # Découpage si > 2000 caractères
                if len(full_response) <= 2000:
                    await ctx.reply(full_response)
                else:
                    chunks = [full_response[i:i+1900] for i in range(0, len(full_response), 1900)]
                    for chunk in chunks:
                        await ctx.send(chunk)
            except Exception as exc:
                await ctx.reply(f"❌ Erreur lors de l'exécution d'E-ZzIO : {exc}")

    @commands.command(name="ez-status", help="Statut de santé des modèles et composants")
    async def status_ezzio(self, ctx: commands.Context):
        health = await check_ollama_health()
        status_icon = "🟢" if health.ollama_ok else "🔴"
        models_str = ", ".join(health.models_available[:4])
        await ctx.reply(
            f"{status_icon} **Statut E-ZzIO Core :**\n"
            f"• Serveur LLM : {'En ligne' if health.ollama_ok else 'Hors ligne'}\n"
            f"• Base Vectorielle : {'Opérationnelle' if health.vectorstore_ok else 'Non initialisée'}\n"
            f"• Modèles : `{models_str}`"
        )

    @commands.command(name="ez-heal", help="Lance un diagnostic et auto-guérison du code source")
    async def heal_ezzio(self, ctx: commands.Context):
        async with ctx.typing():
            healer = AutoHealer()
            diag = healer.diagnose_all()
            if diag["healthy"]:
                await ctx.reply(f"✅ Codebase 100% intègre : {diag['syntax_valid_count']}/{diag['python_modules']} modules Python validés par AST.")
            else:
                await ctx.reply(f"⚠️ {len(diag['syntax_errors'])} anomalie(s) détectée(s).")


class EzzioDiscordBot(commands.Bot):
    def __init__(self, command_prefix: str = "!"):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=command_prefix, intents=intents)

    async def setup_hook(self) -> None:
        await self.add_cog(EzzioCog(self))
        logger.info("Cog E-ZzIO chargé avec succès sur le bot Discord.")


def create_ezzio_bot(command_prefix: str = "!") -> EzzioDiscordBot:
    return EzzioDiscordBot(command_prefix=command_prefix)
