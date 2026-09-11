"""E-ZZIO — publication long-format Discord (guides / forum).

Découpe Markdown sûre (<2000 car.) : jamais au milieu d'un bloc ``` ;
coupe préférentielle aux paragraphes. Envoi séquentiel.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ezzio.discord.publisher")

DISCORD_LIMIT = 1950
FENCE = "```"


def split_markdown(text: str, limit: int = DISCORD_LIMIT) -> List[str]:
    """Découpe sans jamais couper un bloc de code ; ferme/rouvre les fences."""
    paras = re.split(r"\n{2,}", text)
    chunks: List[str] = []
    cur: List[str] = []
    cur_len = 0
    in_fence = False

    def flush():
        nonlocal cur, cur_len, in_fence
        if not cur:
            return
        body = "\n\n".join(cur)
        if in_fence:
            body += f"\n{FENCE}"
        chunks.append(body)
        cur, cur_len = [], 0

    for para in paras:
        fences = para.count(FENCE)
        # Paragraphe trop long seul : flush d'abord, puis découpe isolée
        if len(para) > limit and cur:
            flush()
        while len(para) > limit:
            cut = para.rfind("\n", 0, limit)
            if cut < limit // 2:
                cut = limit
            # ne jamais couper à l'intérieur d'un fence ouvert
            head = para[:cut]
            if (head.count(FENCE) + (1 if in_fence else 0)) % 2 == 1:
                # referme puis rouvre
                cur.append(head + f"\n{FENCE}")
                cur_len += len(head)
                flush()
                in_fence = True
                para = f"{FENCE}\n" + para[cut:].lstrip("\n")
            else:
                cur.append(head)
                flush()
                para = para[cut:].lstrip("\n")
            if fences == 0 and len(para) <= limit:
                break
        if fences % 2 == 1:
            in_fence = not in_fence
        add = len(para) + 2
        if cur and cur_len + add > limit:
            flush()
        cur.append(para)
        cur_len += add
    flush()
    return [c for c in chunks if c.strip()]


class DiscordPublisher:
    """Publie des guides longs : thread forum si possible, sinon chunks."""

    def __init__(self, bot=None):
        self.bot = bot

    async def ensure_thread(self, channel: Any, title: str) -> tuple[Any, int | None]:
        """Crée un fil éphémère (texte/forum) ; retourne (cible, thread_id|None)."""
        import discord

        try:
            if isinstance(channel, discord.ForumChannel):
                thread = await channel.create_thread(
                    name=title[:100],
                    content="Guide E-ZZIO : " + title,
                )
                target = thread.thread or thread
                return target, getattr(target, "id", None)
            if isinstance(channel, discord.TextChannel):
                thread = await channel.create_thread(
                    name=f"Guide : {title[:80]}",
                    auto_archive_duration=60,
                )
                return thread, getattr(thread, "id", None)
        except Exception as exc:
            logger.warning("[PUBLISHER] Thread impossible, repli salon : %s", exc)
        return channel, None

    async def post_guide(
        self,
        channel: Any,
        title: str,
        content_markdown: str,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        import discord

        target = channel
        thread_created = False
        if isinstance(channel, discord.ForumChannel):
            thread = await channel.create_thread(
                name=title[:100],
                content="Guide E-ZZIO : " + title,
            )
            target = thread.thread or thread
            thread_created = True
        header = f"**{title}**\n" + (f"{' '.join(tags)}\n" if tags else "") + "━" * 20
        chunks = split_markdown(header + "\n\n" + content_markdown)
        sent = 0
        for i, chunk in enumerate(chunks):
            if i == 0 and hasattr(target, "reply") and not thread_created:
                await target.reply(chunk)
            else:
                await target.send(chunk)
            sent += 1
        logger.info("[PUBLISHER] Guide '%s' publié en %d chunk(s).", title, sent)
        return {"ok": True, "chunks": sent, "thread": thread_created}
