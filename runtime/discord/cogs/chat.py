import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional, Literal

from runtime.core.ezzio_core import EzzioCore
from core.memory.unified_gateway import UnifiedMemoryGateway

logger = logging.getLogger("ezzio.discord.chat")

class ChatCog(commands.Cog):
    """Cog Discord pour les interactions conversationnelles, le rappel et la gestion mémorielle."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.memory_gw = UnifiedMemoryGateway("runtime/evidence/evidence.db")
        self.core = EzzioCore(memory_gateway=self.memory_gw)
        self._initialized = False

    async def cog_load(self):
        if not self._initialized:
            await self.core.init()
            self._initialized = True
            logger.info("[OK] EzzioCore et UnifiedMemoryGateway initialisés pour Discord.")

    @app_commands.command(name="chat", description="Discute avec E-ZZIO en local (100% CPU souverain)")
    @app_commands.describe(message="Ton message ou question technique")
    async def chat(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(thinking=True)
        user_id = str(interaction.user.id)
        session_id = f"disc_user_{user_id}"

        try:
            result = await self.core.think(user_id=user_id, message=message, session_id=session_id)
            response_text = result.get("response", "Aucune réponse générée.")
            provider = result.get("provider", "local").upper()
            intent = result.get("intent", "chat").upper()

            embed = discord.Embed(description=response_text, color=discord.Color.teal())
            embed.set_footer(text=f"E-ZZIO Autonomous | Intent: {intent} | Provider: {provider}")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"[ERREUR] Échec /chat: {e}", exc_info=True)
            await interaction.followup.send(
                embed=discord.Embed(description=f"❌ Erreur lors du traitement : `{str(e)}`", color=discord.Color.red())
            )

    @app_commands.command(name="recall", description="Recherche dans la mémoire long terme cross-session et les preuves")
    @app_commands.describe(
        sujet="Sujet, fait ou consigne passée à retrouver",
        limite="Nombre maximal d'éléments mémoriels à inspecter (1 à 10)"
    )
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
                    description=f"Aucune trace trouvée dans la mémoire long terme pour : `\"{sujet}\"`.",
                    color=discord.Color.dark_grey()
                )
                embed_empty.set_footer(text="Base SQLite WAL : 0 résultat")
                await interaction.followup.send(embed=embed_empty)
                return

            context_blocks = []
            if evidences:
                context_blocks.append(f"**Preuves archivées ({len(evidences)}) :**")
                for ev in evidences[:3]:
                    context_blocks.append(f"- `[{ev.get('provider', 'N/A')}]` {ev.get('query')}")

            if chat_history:
                context_blocks.append(f"\n**Échanges cross-session ({len(chat_history)}) :**")
                for msg in chat_history[:4]:
                    role = msg.get("role", "user").capitalize()
                    content = msg.get("content", "").replace("\n", " ")[:140]
                    context_blocks.append(f"- **{role}** : {content}")

            context_str = "\n".join(context_blocks)

            synth_prompt = (
                f"Voici les traces mémorielles retrouvées dans la base de données concernant '{sujet}' :\n"
                f"{context_str}\n\n"
                f"Consigne : Rédige une synthèse factuelle et concise (2-3 phrases) de ce qui a été fait ou abordé sur ce sujet."
            )

            core_result = await self.core.think(
                user_id=user_id,
                message=synth_prompt,
                session_id=f"disc_recall_{user_id}"
            )
            synthesis_text = core_result.get("response", "").strip()

            embed = discord.Embed(
                title=f"🧠 Rappel Mémoriel : \"{sujet}\"",
                description=synthesis_text if synthesis_text else "Synthèse des faits extraits de la base de persistance.",
                color=discord.Color.purple()
            )
            embed.add_field(name="📦 Contexte extrait de la base WAL", value=context_str[:1024], inline=False)
            embed.set_footer(text=f"E-ZZIO Memory Engine | {total_found} trace(s) extraite(s) | SQLite WAL")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"[ERREUR] Échec /recall: {e}", exc_info=True)
            await interaction.followup.send(
                embed=discord.Embed(description=f"❌ Erreur lors du rappel mémoriel : `{str(e)}`", color=discord.Color.red())
            )

    @app_commands.command(name="forget", description="Purger ou réinitialiser la mémoire contextuelle dans SQLite WAL")
    @app_commands.describe(
        portee="Portée de la purge mémorielle",
        mot_cle="Mot-clé spécifique à supprimer (requis si 'par_mot_cle' est sélectionné)"
    )
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
                embed = discord.Embed(
                    title="🧹 Mémoire de session réinitialisée",
                    description=f"**{deleted}** message(s) supprimé(s) pour la session courante (`{session_id}`).",
                    color=discord.Color.orange()
                )

            elif portee == "tout_mon_historique":
                deleted = await self.memory_gw.clear_user_history(user_id)
                embed = discord.Embed(
                    title="🗑️ Historique complet utilisateur purgé",
                    description=f"**{deleted}** message(s) supprimé(s) sur toutes tes sessions Discord.",
                    color=discord.Color.red()
                )

            elif portee == "par_mot_cle":
                if not mot_cle or not mot_cle.strip():
                    await interaction.followup.send(
                        embed=discord.Embed(
                            description="⚠️ Veuillez fournir un `mot_cle` pour la purge ciblée.",
                            color=discord.Color.gold()
                        )
                    )
                    return
                
                res = await self.memory_gw.purge_by_keyword(mot_cle.strip())
                embed = discord.Embed(
                    title=f"🎯 Purge ciblée : \"{mot_cle.strip()}\"",
                    description=(
                        f"- **Messages supprimés :** {res['messages_deleted']}\n"
                        f"- **Preuves supprimées :** {res['evidences_deleted']}"
                    ),
                    color=discord.Color.dark_gold()
                )

            embed.set_footer(text="Base SQLite WAL — Opération irréversible")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"[ERREUR] Échec /forget: {e}", exc_info=True)
            await interaction.followup.send(
                embed=discord.Embed(description=f"❌ Erreur lors de la purge : `{str(e)}`", color=discord.Color.red())
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(ChatCog(bot))
