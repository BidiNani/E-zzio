"""E-ZZIO — règles de routage Discord (pures, sans effet de bord)."""
from __future__ import annotations

BIDINANI_BUS_CATEGORY_ID = 1519013325822755097


def channel_category_id(channel) -> int | None:
    """Catégorie du salon, fils/threads inclus via parent."""
    cid = getattr(channel, "category_id", None)
    if cid is not None:
        return cid
    return getattr(getattr(channel, "parent", None), "category_id", None)


def should_respond(
    is_private: bool,
    category_id: int | None,
    mentioned: bool,
    content: str,
    bot_id: int | None = None,
) -> tuple[bool, str]:
    """Décide (répondre, prompt nettoyé)."""
    txt = (content or "").strip()
    if is_private:
        return (bool(txt), txt)
    if category_id == BIDINANI_BUS_CATEGORY_ID:
        return (bool(txt), txt)
    if txt.startswith("!e "):
        return True, txt[3:].strip()
    if txt.startswith("!ezzio "):
        return True, txt[7:].strip()
    if mentioned:
        clean = txt
        if bot_id is not None:
            clean = clean.replace(f"<@{bot_id}>", "").replace(f"<@!{bot_id}>", "")
        return True, clean.strip()
    return False, ""
