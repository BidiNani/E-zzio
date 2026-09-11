"""E-ZZIO — composants interactifs Discord + rendu progressif throttlé.

StreamEditor : révélation progressive d'un texte déjà complet
(premier paint >20 car., ≤1 édition/900 ms, édition finale).
Pas de flux token (API /master/chat non-SSE) — rendu seul.
"""
from __future__ import annotations

import asyncio
import io
import logging
import re
import time
from typing import Any, Awaitable, Callable, List

logger = logging.getLogger("ezzio.discord.ui")

FIRST_PAINT_MIN = 20
EDIT_INTERVAL_SEC = 0.9
DISCORD_LIMIT = 1950
CODE_FENCE_RE = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)


def format_ezzio_response(content: str, provider: str, model: str,
                          latency_ms: float, mission: str = "STANDARD",
                          status: str = "SUCCESS") -> str:
    """En-tête de télémétrie obligatoire devant chaque restitution."""
    latency_sec = f"{latency_ms / 1000:.2f}s"
    header = (
        "E-ZZIO\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"Mission  : {mission}\n"
        f"Provider : {provider}\n"
        f"Model    : {model}\n"
        f"Latency  : {latency_sec}\n"
        f"Status   : {status}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )
    return header + (content or "")


def extract_code_blocks(markdown: str) -> str:
    """Isole les blocs de code d'un guide."""
    blocks = CODE_FENCE_RE.findall(markdown)
    if not blocks:
        return "_Aucun bloc de code._"
    return "\n\n".join(f"```\n{b.strip()}\n```" for b in blocks)


def progressive_plan(text: str, limit: int = DISCORD_LIMIT) -> List[str]:
    """Snapshots croissants pour révélation (pur, testable)."""
    text = text or ""
    if len(text) <= max(FIRST_PAINT_MIN, 1):
        return [text] if text else []
    snaps = [text[: FIRST_PAINT_MIN + 5]]
    step = max(limit // 3, FIRST_PAINT_MIN)
    pos = FIRST_PAINT_MIN + 5
    while pos < len(text):
        pos = min(pos + step, len(text))
        snaps.append(text[:pos])
    if snaps[-1] != text:
        snaps.append(text)
    return snaps


class StreamEditor:
    """Affiche un texte par éditions throttlées (anti-429)."""

    def __init__(self, interval: float = EDIT_INTERVAL_SEC,
                 limit: int = DISCORD_LIMIT):
        self.interval = interval
        self.limit = limit
        self._last_edit = 0.0

    async def render(self, send_first: Callable[[str], Awaitable[Any]],
                     text: str) -> None:
        """send_first(chunk) -> objet avec .edit(content=)."""
        snaps = progressive_plan(text, self.limit)
        if not snaps:
            return
        msg = await send_first(snaps[0][: self.limit])
        edit = getattr(msg, "edit", None)
        for snap in snaps[1:]:
            delay = self.interval - (time.monotonic() - self._last_edit)
            if delay > 0:
                await asyncio.sleep(delay)
            if edit is None:
                msg = await send_first(snap[: self.limit])
                edit = getattr(msg, "edit", None)
                continue
            await edit(content=snap[: self.limit])
            self._last_edit = time.monotonic()
        # Édition finale exacte (fin du flux, typing déjà clos par l'appelant)
        if edit is not None:
            await edit(content=text[: self.limit])


def build_guide_view(pages: List[str], title: str, full_markdown: str):
    """GuideNavigationView : pagination + export .md + extraction code."""
    import discord

    class GuideNavigationView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=600)
            self.pages = pages
            self.idx = 0
            self.title = title
            self.full = full_markdown

        async def _show(self, interaction, content: str):
            await interaction.response.edit_message(content=content, view=self)

        @discord.ui.button(label="⬅ Précédent", style=discord.ButtonStyle.secondary)
        async def prev_btn(self, interaction, button):
            self.idx = (self.idx - 1) % len(self.pages)
            await self._show(interaction, self.pages[self.idx])

        @discord.ui.button(label="Suivant ➡", style=discord.ButtonStyle.secondary)
        async def next_btn(self, interaction, button):
            self.idx = (self.idx + 1) % len(self.pages)
            await self._show(interaction, self.pages[self.idx])

        @discord.ui.button(label="💾 Exporter .md", style=discord.ButtonStyle.success)
        async def export_btn(self, interaction, button):
            buf = io.BytesIO(self.full.encode("utf-8"))
            await interaction.response.send_message(
                file=discord.File(buf, filename="guide-ezzio.md"),
                ephemeral=True,
            )

        @discord.ui.button(label="💻 Extraire Code", style=discord.ButtonStyle.primary)
        async def code_btn(self, interaction, button):
            code = extract_code_blocks(self.full)[:DISCORD_LIMIT]
            await interaction.response.send_message(code, ephemeral=True)

    return GuideNavigationView()
