"""E-ZZIO — voix cloud Discord : Edge-TTS → VoiceClient (FFmpeg).

STT Groq : NON câblé (pool Groq 403 constaté) — module prêt à recevoir
un transcripteur dès le rétablissement du pool.
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("ezzio.discord.voice")

DEFAULT_VOICE = "fr-FR-DeniseNeural"
GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_STT_MODEL = "whisper-large-v3"
_locks: Dict[int, asyncio.Lock] = {}


def resolve_groq_key() -> Optional[str]:
    """DISCORD_GROQ_API_KEY prioritaire, repli GROQ_API_KEY / _2 (env + secrets/.env)."""
    import os
    for name in ("DISCORD_GROQ_API_KEY", "GROQ_API_KEY", "GROQ_API_KEY_2"):
        val = (os.getenv(name) or "").strip().strip("\"'")
        if val:
            return val
    try:
        from pathlib import Path as _P
        env = _P("G:/AI/E-zzio/secrets/.env")
        if env.exists():
            for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
                s = line.strip()
                if not s or s.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                if k.strip() in ("DISCORD_GROQ_API_KEY", "GROQ_API_KEY", "GROQ_API_KEY_2"):
                    v = v.strip().strip("\"'")
                    if v:
                        return v
    except Exception as exc:
        logger.warning("[VOICE] lecture secrets/.env impossible : %s", exc)
    return None


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> tuple[bool, str]:
    """STT Groq Whisper Large v3 (async, réseau explicite si anomalie)."""
    import aiohttp
    key = resolve_groq_key()
    if not key:
        return False, "Clé Groq absente (DISCORD_GROQ_API_KEY / GROQ_API_KEY)."
    try:
        timeout = aiohttp.ClientTimeout(total=60.0)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            form = aiohttp.FormData()
            form.add_field("file", audio_bytes, filename=filename,
                           content_type="audio/wav")
            form.add_field("model", GROQ_STT_MODEL)
            form.add_field("language", "fr")
            async with session.post(
                GROQ_STT_URL,
                headers={"Authorization": f"Bearer {key}"},
                data=form,
            ) as resp:
                if resp.status != 200:
                    body = (await resp.text())[:200]
                    logger.error("[VOICE] STT Groq HTTP %s : %s", resp.status, body)
                    return False, f"STT Groq HTTP {resp.status}."
                data = await resp.json()
                text = str(data.get("text", "")).strip()
                return (True, text) if text else (False, "Transcription vide.")
    except Exception as exc:
        logger.error("[VOICE] STT Groq anomalie réseau : %s", exc)
        return False, f"STT anomalie réseau : {exc}"


def _guild_lock(guild_id: int) -> asyncio.Lock:
    lock = _locks.get(guild_id)
    if lock is None:
        lock = asyncio.Lock()
        _locks[guild_id] = lock
    return lock


async def synthesize_mp3(text: str, voice: str = DEFAULT_VOICE) -> Path:
    """Génère un MP3 temporaire via Edge-TTS (100 % cloud, tâche async)."""
    try:
        import edge_tts
    except Exception as exc:
        raise RuntimeError(f"edge-tts indisponible : {exc}") from exc
    out = Path(tempfile.mkdtemp(prefix="ezzio-tts-")) / "out.mp3"
    await edge_tts.Communicate(text[:2000], voice).save(str(out))
    return out


async def join_author_channel(message) -> tuple[bool, str]:
    """!e join : rejoint le salon vocal de l'auteur."""
    voice_state = getattr(message.author, "voice", None)
    channel = getattr(voice_state, "channel", None)
    if channel is None:
        return False, "Rejoins d'abord un salon vocal."
    vc = message.guild.voice_client if message.guild else None
    try:
        if vc is None or not vc.is_connected():
            await channel.connect()
        elif vc.channel != channel:
            await vc.move_to(channel)
        return True, f"Connecté à `{channel.name}`."
    except Exception as exc:
        logger.error("[VOICE] join impossible : %s", exc)
        return False, f"Connexion vocale impossible : {exc}"


async def leave_channel(message) -> tuple[bool, str]:
    """!e leave : quitte le salon vocal."""
    vc = message.guild.voice_client if message.guild else None
    if vc is None or not vc.is_connected():
        return False, "Pas de connexion vocale active."
    try:
        await vc.disconnect(force=True)
        return True, "Déconnecté du salon vocal."
    except Exception as exc:
        return False, f"Déconnexion impossible : {exc}"


async def speak(message, text: str, voice: str = DEFAULT_VOICE) -> tuple[bool, str]:
    """!e speak <texte> : synthèse Edge-TTS lue dans le VoiceClient."""
    if message.guild is None:
        return False, "Commande vocale disponible uniquement en salon."
    vc = message.guild.voice_client
    if vc is None or not vc.is_connected():
        ok, info = await join_author_channel(message)
        if not ok:
            return False, info
        vc = message.guild.voice_client
    lock = _guild_lock(message.guild.id)
    async with lock:
        try:
            mp3 = await synthesize_mp3(text, voice)
        except Exception as exc:
            return False, f"Synthèse impossible : {exc}"
        try:
            import discord
            if vc.is_playing():
                vc.stop()
            src = discord.FFmpegPCMAudio(str(mp3))
            done = asyncio.Event()
            vc.play(src, after=lambda _e: None)

            async def _waiter():
                while vc.is_playing():
                    await asyncio.sleep(0.2)
                done.set()

            waiter = asyncio.create_task(_waiter())
            await asyncio.wait_for(done.wait(), timeout=120.0)
            waiter.cancel()
            return True, f"Lu ({len(text)} car.)."
        except Exception as exc:
            logger.error("[VOICE] lecture impossible : %s", exc)
            return False, f"Lecture impossible : {exc}"
        finally:
            try:
                mp3.unlink(missing_ok=True)
                mp3.parent.rmdir()
            except Exception:
                pass
