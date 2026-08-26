"""
E-ZZIO — Presence Layer / Discord Interface (Couche 1)
=======================================================
Interface humaine Discord d'E-ZZIO.

Cette couche:
  - gère les événements Discord (on_message, typing, slash commands)
  - rend la personnalité d'E-ZZIO (PersonalityRenderer)
  - chunke les réponses longues
  - ne contient AUCUNE logique cognitive
  - ne sait pas quel modèle a répondu (sauf pour le footer)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from runtime.bidi.ezzio_interface import BidiEzzioInterface, BidiResponse

logger = logging.getLogger("ezzio.discord.presence")

DISCORD_MAX_CHARS = 1990  # Discord limit is 2000; leave margin


class PersonalityRenderer:
    """
    Renders BidiResponse into Discord-ready content.
    All personality is in this class — nowhere else.
    """

    THINKING_MESSAGES = [
        "Je regarde ça...",
        "Un instant, j'analyse.",
        "Je m'en occupe.",
        "Laisse-moi vérifier.",
        "Je traite ta demande...",
    ]

    def __init__(self):
        self._think_idx = 0

    def thinking_message(self) -> str:
        msg = self.THINKING_MESSAGES[self._think_idx % len(self.THINKING_MESSAGES)]
        self._think_idx += 1
        return msg

    def render_embed(self, response: BidiResponse) -> discord.Embed:
        if response.is_error:
            color = discord.Color.red()
        elif response.task_type == "code_simple":
            color = discord.Color.blue()
        elif response.task_type == "deep_reasoning":
            color = discord.Color.purple()
        else:
            color = discord.Color.teal()

        embed = discord.Embed(description=response.display_text[:4096], color=color)
        embed.set_footer(text=response.footer)
        return embed

    def split_text(self, text: str) -> list[str]:
        if len(text) <= DISCORD_MAX_CHARS:
            return [text]
        chunks = []
        while text:
            chunk = text[:DISCORD_MAX_CHARS]
            cut = chunk.rfind("\n")
            if cut > DISCORD_MAX_CHARS // 2:
                chunk = chunk[:cut]
            chunks.append(chunk)
            text = text[len(chunk):]
        return chunks


class EzzioDiscordBot(commands.Bot):
    """
    Couche 1 : Interface Discord d'E-ZZIO.

    Ce que ce bot fait :
      - Répond aux mentions, DMs, et commandes (!ezzio, !e-zzio)
      - Affiche l'indicateur de frappe (typing)
      - Délègue tout traitement à BidiEzzioInterface → OrganismKernel

    Ce que ce bot ne fait PAS :
      - Choisir un modèle
      - Appeler un provider directement
      - Stocker de l'état conversationnel propre à Discord
    """

    def __init__(self, interface: Optional[BidiEzzioInterface] = None, **kwargs):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents, **kwargs)
        self.interface = interface or BidiEzzioInterface()
        self.renderer = PersonalityRenderer()

    async def setup_hook(self):
        try:
            synced = await self.tree.sync()
            logger.info(f"[E-ZZIO] Slash commands synced: {[c.name for c in synced]}")
        except Exception as e:
            logger.error(f"[E-ZZIO] Slash sync error: {e}")

    async def on_ready(self):
        logger.info(f"[E-ZZIO] Online as {self.user} (ID: {self.user.id if self.user else 'UNKNOWN'})")
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name="Ledger actif")
        )

    def _should_respond(self, message: discord.Message) -> bool:
        if message.author == self.user or message.author.bot:
            return False
        is_dm      = isinstance(message.channel, discord.DMChannel)
        is_mention = self.user in message.mentions if self.user else False
        is_named   = any(k in message.content.lower() for k in ("e-zzio", "ezzio"))
        is_cmd     = message.content.startswith(("!ezzio ", "!e-zzio ", "!chat "))
        return is_dm or is_mention or is_named or is_cmd

    async def _process_and_reply(self, message: discord.Message, content: str):
        author_id  = str(message.author.id)
        session_id = f"ezzio_disc_{author_id}"

        normalized = self.interface.normalize(
            bot_id=self.user.id if self.user else None,
            content=content,
        )

        async with message.channel.typing():
            response: BidiResponse = await self.interface.handle(
                author_id=author_id,
                content=normalized,
                session_id=session_id,
            )

        if len(response.display_text) <= 4000:
            await message.reply(embed=self.renderer.render_embed(response), mention_author=False)
        else:
            chunks = self.renderer.split_text(response.display_text)
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await message.reply(chunk, mention_author=False)
                else:
                    await message.channel.send(chunk)
            footer_embed = discord.Embed(color=discord.Color.teal())
            footer_embed.set_footer(text=response.footer)
            await message.channel.send(embed=footer_embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self._should_respond(message):
            await self.process_commands(message)
            return
        await self._process_and_reply(message, message.content)
        await self.process_commands(message)


def register_slash_commands(bot: EzzioDiscordBot):
    """Register /ezzio and /status slash commands."""

    @bot.tree.command(name="ezzio", description="Envoie un message à E-ZZIO")
    @app_commands.describe(message="Ton message ou question technique")
    async def slash_ezzio(interaction: discord.Interaction, message: str):
        await interaction.response.defer(thinking=True)
        author_id  = str(interaction.user.id)
        session_id = f"ezzio_disc_{author_id}"
        normalized = bot.interface.normalize(bot_id=None, content=message)
        response   = await bot.interface.handle(
            author_id=author_id,
            content=normalized,
            session_id=session_id,
        )
        await interaction.followup.send(embed=bot.renderer.render_embed(response))

    @bot.tree.command(name="status", description="Affiche l'état du noyau E-ZZIO")
    async def slash_status(interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        try:
            kernel = bot.interface._get_kernel()
            status = kernel.get_organism_status()
            hw     = status.get("hardware", {})
            ledger = status.get("decision_ledger", {})
            embed  = discord.Embed(title="🧠 E-ZZIO Kernel Status", color=discord.Color.green())
            embed.add_field(name="Global", value=status.get("global_state", "?"),                   inline=True)
            embed.add_field(name="Ledger", value=ledger.get("status", "?"),                          inline=True)
            embed.add_field(name="Blocs",  value=str(ledger.get("decisions_recorded", "?")),         inline=True)
            embed.add_field(name="CPU",    value=f"{hw.get('cpu_system_usage_percent', '?')}%",      inline=True)
            embed.add_field(name="RAM",    value=f"{hw.get('ram_usage_percent', '?')}%",             inline=True)
            embed.add_field(name="Gaming", value=str(hw.get("gaming_detected", "?")),                inline=True)
            embed.set_footer(text="E-ZZIO | Kernel Live Status")
            await interaction.followup.send(embed=embed)
        except Exception as exc:
            await interaction.followup.send(
                embed=discord.Embed(description=f"❌ Erreur status: `{exc}`", color=discord.Color.red())
            )
