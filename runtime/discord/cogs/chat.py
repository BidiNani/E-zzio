import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional, Literal

from runtime.core.ezzio_core import EzzioCore
from core.memory.unified_gateway import UnifiedMemoryGateway
from core.providers.gemini_provider import GeminiProvider

logger = logging.getLogger("ezzio.discord.chat")

class ChatCog(commands.Cog):
    """Cog Discord durci avec mémoire FTS5 et fallback automatique Cloud."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.memory_gw = UnifiedMemoryGateway("runtime/evidence/evidence.db")
        self.core = EzzioCore(memory_gateway=self.memory_gw)
        self.cloud_fallback = GeminiProvider()
        self._initialized = False

    async def cog_load(self):
        if not self._initialized:
            await self.core.init()
            self._initialized = True
            logger.info("[OK] EzzioCore et UnifiedMemoryGateway initialisés.")

    @app_commands.command(name="chat", description="Discute avec E-ZZIO (100% CPU avec fallback Cloud)")
    @app_commands.describe(message="Ton message ou question technique")
    async def chat(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(thinking=True)
        user_id = str(interaction.user.id)
        session_id = f"disc_user_{user_id}"

        try:
            # 1. Tentative locale TIER-1
            result = await self.core.think(user_id=user_id, message=message, session_id=session_id)
            response_text = result.get("response", "Aucune réponse.")
            provider = result.get("provider", "ollama").upper()
            intent = result.get("intent", "chat").upper()

            embed = discord.Embed(description=response_text, color=discord.Color.teal())
            embed.set_footer(text=f"E-ZZIO Autonomous | Intent: {intent} | Provider: {provider}")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.warning(f"[*] Incident TIER-1 ({e}). Bascule immédiate vers Gemini Cloud Fallback...")
            try:
                # 2. Repli résilient TIER-2
                cloud_res = await self.cloud_fallback.search(f"Réponds de façon concise et technique : {message}")
                cloud_text = cloud_res.get("data", {}).get("text", "Réponse indisponible.")
                
                await self.memory_gw.record_message(
                    session_id, "assistant", cloud_text, metadata={"provider": "gemini", "fallback": True}
                )
                
                embed = discord.Embed(description=cloud_text, color=discord.Color.gold())
                embed.set_footer(text="E-ZZIO Autonomous | Provider: GEMINI (Auto-Fallback)")
                await interaction.followup.send(embed=embed)
            except Exception as ex_cloud:
                logger.error(f"[ERREUR] Échec total de la chaîne de réponse: {ex_cloud}")
                await interaction.followup.send(
                    embed=discord.Embed(
                        description=f"❌ Tous les moteurs d'inférence sont temporairement indisponibles : `{str(ex_cloud)}`",
                        color=discord.Color.red()
                    )
                )

    @app_commands.command(name="recall", description="Recherche mémorielle FTS5 BM25 et synthèse")
    @app_commands.describe(sujet="Sujet à retrouver", limite="Nombre de traces (1 à 10)")
    async def recall(self, interaction: discord.Interaction, sujet: str, limite: Optional[int] = 5):
        await interaction.response.defer(thinking=True)
        user_id = str(interaction.user.id)
        limit_val = max(1, min(limite or 5, 10))

        try:
            mem_results = await self.memory_gw.search_memory(query=sujet, limit=limit_val)
            evidences = mem_results.get("evidences", [])
            chat_history = mem_results.get("chat_history", [])
            total_found = len(evidences) + len(chat_history)

            if total_found == 0:
                embed_empty = discord.Embed(
                    title="🧠 Rappel Mémoriel E-ZZIO",
                    description=f"Aucune trace trouvée pour : `\"{sujet}\"`.",
                    color=discord.Color.dark_grey()
                )
                embed_empty.set_footer(text="Base SQLite FTS5 BM25 : 0 résultat")
                await interaction.followup.send(embed=embed_empty)
                return

            context_blocks = []
            if evidences:
                context_blocks.append(f"**Preuves ({len(evidences)}) :**")
                for ev in evidences[:3]:
                    context_blocks.append(f"- `[{ev.get('provider')}]` {ev.get('query')}")

            if chat_history:
                context_blocks.append(f"\n**Échanges indexés ({len(chat_history)}) :**")
                for msg in chat_history[:4]:
                    role = msg.get("role", "user").capitalize()
                    content = msg.get("content", "").replace("\n", " ")[:140]
                    context_blocks.append(f"- **{role}** : {content}")

            context_str = "\n".join(context_blocks)
            synth_prompt = f"Traces mémorielles FTS5 sur '{sujet}' :\n{context_str}\n\nConsigne : Synthétise en 2 phrases."

            core_result = await self.core.think(user_id=user_id, message=synth_prompt, session_id=f"disc_recall_{user_id}")
            synthesis_text = core_result.get("response", "").strip()

            embed = discord.Embed(title=f"🧠 Rappel Mémoriel : \"{sujet}\"", description=synthesis_text, color=discord.Color.purple())
            embed.add_field(name="📦 Traces FTS5 extraites", value=context_str[:1024], inline=False)
            embed.set_footer(text=f"E-ZZIO Memory Engine | {total_found} trace(s) | FTS5 BM25")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"[ERREUR] /recall : {e}", exc_info=True)
            await interaction.followup.send(embed=discord.Embed(description=f"❌ Erreur : `{str(e)}`", color=discord.Color.red()))

    @app_commands.command(name="forget", description="Purger ou réinitialiser la mémoire contextuelle dans SQLite WAL")
    @app_commands.describe(portee="Portée de la purge", mot_cle="Mot-clé requis si 'par_mot_cle'")
    async def forget(
        self,
        interaction: discord.Interaction,
        portee: Literal["cette_session", "tout_mon_historique", "par_mot_cle"],
        mot_cle: Optional[str] = None
    ):
        await interaction.response.defer(thinking=True)
        user_id = str(interaction.user.id)
        session_id = f"disc_user_{user_id}"

        try:
            if portee == "cette_session":
                deleted = await self.memory_gw.clear_session(session_id)
                desc = f"**{deleted}** message(s) supprimé(s) pour `{session_id}`."
            elif portee == "tout_mon_historique":
                deleted = await self.memory_gw.clear_user_history(user_id)
                desc = f"**{deleted}** message(s) supprimé(s) pour tout ton compte."
            elif portee == "par_mot_cle":
                if not mot_cle or not mot_cle.strip():
                    await interaction.followup.send("⚠️ Spécifiez un `mot_cle`.")
                    return
                res = await self.memory_gw.purge_by_keyword(mot_cle.strip())
                desc = f"- Messages : {res['messages_deleted']}\n- Preuves : {res['evidences_deleted']}"

            embed = discord.Embed(title="🧹 Purge Mémorielle Validée", description=desc, color=discord.Color.orange())
            embed.set_footer(text="Base SQLite WAL & Index FTS5 mis à jour")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(embed=discord.Embed(description=f"❌ Erreur purge : `{str(e)}`", color=discord.Color.red()))

async def setup(bot: commands.Bot):
    await bot.add_cog(ChatCog(bot))
