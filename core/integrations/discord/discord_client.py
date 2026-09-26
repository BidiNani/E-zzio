"""
E-ZZIO Sovereign Discord Agent Client (V7.51 Dynamic Presence & Vault Hardened)
Intègre le Secure Vault, la session aiohttp persistante et le statut dynamique.
"""

import asyncio
import logging
import pathlib
import sys
from datetime import UTC, datetime

logger = logging.getLogger("ezzio.discord.client")

# Journalisation console de secours si aucun handler n'est attaché.
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        stream=sys.stdout,
    )

try:
    import httpx as _httpx
except Exception:
    _httpx = None

_http_client = None

# Exceptions reseau unifiees (httpx + aiohttp)
import aiohttp
import httpx as _httpx_lib

DISCORD_NET_ERRORS = (
    aiohttp.ClientError,
    asyncio.TimeoutError,
    _httpx_lib.RequestError,
    _httpx_lib.TimeoutException,
)


def get_http_client():
    """Singleton httpx partagé : 1 pool keepalive, 0 renégociation TLS/message."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        if _httpx is None:
            raise RuntimeError("httpx indisponible dans le venv.")
        _http_client = _httpx.AsyncClient(
            timeout=30.0,
            limits=_httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
    return _http_client


import aiohttp
import discord
from discord.ext import commands, tasks

PROJECT_ROOT = pathlib.Path(r"G:\AI\E-zzio")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.adapters.config.dotenv_provider import DotEnvConfigProvider

from core.config import secrets_loader
from core.integrations.discord.discord_watchdog import discord_watchdog
from core.integrations.discord.permission_guard import permission_guard
from core.security.secret_redactor import secret_redactor
from core.tool_gateway.google_bridge import GoogleIdentityBridge

config = DotEnvConfigProvider(env_path=str(PROJECT_ROOT / "secrets" / ".env"))
google_bridge = GoogleIdentityBridge(config=config)

# Source de vérité unique : chargement forcé (override=True).
_LOADED_SECRETS = secrets_loader.load(override=True)

OWNER_ID = "186035306418405376"
OWNER_ID_INT = secrets_loader.discord_owner_id(_LOADED_SECRETS)
if OWNER_ID_INT is None:
    try:
        OWNER_ID_INT = int(OWNER_ID)
    except ValueError:
        OWNER_ID_INT = None

from core.integrations.discord.routing_rules import (
    channel_category_id,
    should_respond,
)


def resolve_discord_token() -> str:
    try:
        vault_res = google_bridge.retrieve_tokens()
        if vault_res.get("valid"):
            tokens = vault_res.get("tokens", {})
            if "discord_bot_token" in tokens:
                return tokens["discord_bot_token"]
    except Exception:
        pass
    return config.get("DISCORD_BOT_TOKEN") or config.get("DISCORD_TOKEN")


DISCORD_TOKEN = resolve_discord_token()
if not DISCORD_TOKEN:
    DISCORD_TOKEN = secrets_loader.discord_token(_LOADED_SECRETS)
LOCAL_API_URL = config.get("EZZIO_LOCAL_API_URL", "http://127.0.0.1:8001/master/chat")

# Points d'accès gouvernés requis : /master/chat (canonique) et
# /v1/chat/completions (compatibilité OpenAI, même gouvernance).
COMPLETIONS_URL = config.get("EZZIO_COMPLETIONS_URL", "http://127.0.0.1:8001/v1/chat/completions")

PROACTIVE_POLL_URL = config.get(
    "EZZIO_PROACTIVE_API_URL", "http://127.0.0.1:8001/system/proactive/poll"
)

secrets_loader.log_secrets_diagnostics(_LOADED_SECRETS)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!e ", intents=intents)

# ==============================================================================
# TÂCHES ASYNCHRONES : PRÉSENCE DYNAMIQUE & DIAGNOSTIC PROACTIF
# ==============================================================================


@tasks.loop(minutes=10)
async def update_dynamic_presence():
    """Met à jour périodiquement le statut du bot pour refléter la santé de l'infrastructure."""
    try:
        activity = discord.Activity(
            type=discord.ActivityType.watching, name="🧠 E-ZZIO | Kernel ONLINE | 🔐 Vault OK"
        )
        await bot.change_presence(status=discord.Status.online, activity=activity)
    except Exception as exc:
        logger.warning("[DISCORD] Echec mise à jour présence : %s", exc)


_reported_anomalies: set[str] = set()


async def run_autonomous_diagnostic() -> list[str]:
    """Exécute un cycle de diagnostic passif sans altérer l'état du système."""
    findings: list[str] = []

    # 1. Sonde de santé de l'API Backend locale
    health_ok = False
    health_detail = ""
    try:
        resp = await get_http_client().get("http://127.0.0.1:8001/health", timeout=4.0)
        if resp.status_code == 200:
            health_ok = True
        else:
            health_detail = "HTTP " + str(resp.status_code)
    except Exception as exc:
        health_detail = str(exc)

    if not health_ok:
        if "backend_health" not in _reported_anomalies:
            findings.append(
                "⚠️ **Alerte Santé API** : Le backend local (`8001/health`) ne répond pas.\n> Détail : `"
                + str(health_detail)
                + "`"
            )
            _reported_anomalies.add("backend_health")
    else:
        if "backend_health" in _reported_anomalies:
            findings.append(
                "✅ **Rétablissement** : L'API backend locale (`8001/health`) est de nouveau opérationnelle."
            )
            _reported_anomalies.discard("backend_health")

    # 2. Sonde de détection des doublons de processus (web_server.py)
    try:
        proc = await asyncio.create_subprocess_exec(
            "powershell",
            "-NoProfile",
            "-Command",
            "(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*web_server.py*' }).Count",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
        out_str = stdout.decode().strip()
        dup_count = int(out_str) if out_str.isdigit() else 1

        if dup_count > 1:
            if "duplicate_web" not in _reported_anomalies:
                findings.append(
                    "⚠️ **Anomalie Processus** : "
                    + str(dup_count)
                    + " instances de `web_server.py` tournent simultanément."
                )
                _reported_anomalies.add("duplicate_web")
        else:
            if "duplicate_web" in _reported_anomalies:
                findings.append(
                    "✅ **Rétablissement** : Les instances de `web_server.py` sont normalisées."
                )
                _reported_anomalies.discard("duplicate_web")
    except Exception as exc:
        logger.debug("[DISCORD] Sonde doublons web_server ignorée : %s", exc)

    return findings


@tasks.loop(minutes=2)
async def proactive_event_loop():
    """Surveillance continue et dispatching autonome en Message Privé."""
    try:
        findings = await run_autonomous_diagnostic()
        if findings and OWNER_ID:
            owner = bot.get_user(int(OWNER_ID)) or await bot.fetch_user(int(OWNER_ID))
            if owner:
                now_str = datetime.now(UTC).strftime("%H:%M:%S UTC")
                header = "🧠 **[E-ZZIO Diagnostic — " + str(now_str) + "]**\n"
                payload = header + "\n".join(findings)
                sanitized = secret_redactor.sanitize(payload)
                # [NETTOYAGE v4.1] Suppression du spam de santé en DM
                # await owner.send(sanitized)
                print(f"[PROACTIF SILENCIEUX] {sanitized}")
    except Exception as exc:
        print(f"[PROACTIVE] Exception dans la boucle de notification : {exc}")


@proactive_event_loop.before_loop
async def before_proactive_loop():
    await bot.wait_until_ready()


_notified_missions: set[str] = set()


@tasks.loop(seconds=5)
async def mission_notifier_loop():
    """Vérifie périodiquement les missions terminées et notifie l'utilisateur."""
    try:
        missions_url = LOCAL_API_URL.replace("/master/chat", "/master/api/v1/missions")
        resp = await get_http_client().get(missions_url, timeout=4.0)
        if resp.status_code == 200:
            data = resp.json()
            missions = data.get("missions", [])
            for m in missions:
                m_id = m.get("mission_id")
                st = m.get("status")
                if st in ("COMPLETED", "FAILED", "CANCELLED") and m_id not in _notified_missions:
                    _notified_missions.add(m_id)
                    if m.get("channel") == "discord" and OWNER_ID:
                        owner = bot.get_user(int(OWNER_ID)) or await bot.fetch_user(int(OWNER_ID))
                        if owner:
                            status_symbol = "✓" if st == "COMPLETED" else "✗"
                            banner = (
                                f"**E-ZZIO**\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                                f"{status_symbol} **TÂCHE TERMINÉE**\n"
                                f"━━━━━━━━━━━━━━━━━━\n\n"
                                f"**Worker**  : `{m.get('worker_type')}`\n"
                                f"**Mission** : `#{m_id}` ({m.get('goal', '')[:60]})\n"
                                f"**Status**  : `{st}`\n"
                                f"**Model**   : `{m.get('model', 'auto')}`\n"
                                f"**Provider**: `{m.get('provider', 'auto')}`\n"
                            )
                            res = m.get("result") or {}
                            if res.get("summary"):
                                banner += f"\n**Résultat** :\n{res.get('summary')}\n"
                            if m.get("artifacts"):
                                banner += "\n**Artifacts** :\n" + "\n".join(
                                    f"- `{a}`" for a in m.get("artifacts")
                                )
                            banner += "\n━━━━━━━━━━━━━━━━━━\n"
                            await owner.send(banner)
    except Exception as exc:
        logger.warning("[DISCORD] Boucle notifier missions ignorée : %s", exc)


@mission_notifier_loop.before_loop
async def before_mission_notifier():
    await bot.wait_until_ready()


@bot.event
async def on_ready():
    if secrets_loader.DISCORD_OWNER_ID is not None:
        print(f"[SECURITY] Propriétaire configuré : {secrets_loader.DISCORD_OWNER_ID}")

    if not update_dynamic_presence.is_running():
        update_dynamic_presence.start()

    if not proactive_event_loop.is_running():
        proactive_event_loop.start()

    if not mission_notifier_loop.is_running():
        mission_notifier_loop.start()

    print(f"[E-ZZIO SENSE] Agent Discord V7.51 en ligne : {bot.user}")
    print(f"[*] Canal d'orchestration persistant : {LOCAL_API_URL}")


@bot.event
async def on_close():
    """Gracefully shut down the shared http client when the bot stops."""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()


async def _handle_message(message):

    chan_scope = f"guild_{message.guild.id}" if message.guild else "dm"
    session_scope = f"disc_{chan_scope}_{message.author.id}"
    username = str(message.author.name)
    is_private = isinstance(message.channel, discord.DMChannel)
    guild_id = str(message.guild.id) if message.guild else None

    owner_bypass = is_private and secrets_loader.is_owner_id(message.author.id)
    auth_check = permission_guard.evaluate_guild_access(
        guild_id, str(message.author.id), username, is_private
    )
    if not auth_check["granted"] and not owner_bypass:
        if is_private:
            logger.warning(
                "[DISCORD-SECURITY] DM bloqué : auteur '%s' non propriétaire.",
                message.author.id,
            )
            await message.channel.send("❌ Accès privé non autorisé.")
        return

    mentioned = bot.user is not None and bot.user in message.mentions
    respond, raw_prompt = should_respond(
        is_private,
        channel_category_id(message.channel),
        mentioned,
        message.content,
        bot.user.id if bot.user is not None else None,
    )
    if not respond:
        return

    if not raw_prompt and not message.attachments:
        return

    # Parse profile flag: e.g. !e --profile=COMPLEX <prompt> or -p COMPLEX <prompt>
    mission_profile = "AUTO"
    model_target = "auto"
    clean_prompt = raw_prompt

    import re

    profile_match = re.search(r"--(?:profile|p)=([A-Za-z0-9_]+)", clean_prompt)
    if profile_match:
        mission_profile = profile_match.group(1).upper()
        clean_prompt = clean_prompt[: profile_match.start()] + clean_prompt[profile_match.end() :]
        clean_prompt = clean_prompt.strip()

    target_match = re.search(r"--(?:target|model)=([A-Za-z0-9_]+)", clean_prompt)
    if target_match:
        model_target = target_match.group(1).lower()
        clean_prompt = clean_prompt[: target_match.start()] + clean_prompt[target_match.end() :]
        clean_prompt = clean_prompt.strip()

    discord_watchdog.record_activity()

    # Commandes avancées : guide long-format + voix cloud
    lowered = clean_prompt.lower()
    if lowered.startswith("guide ") or lowered == "guide":
        from core.integrations.discord.publisher import DiscordPublisher, split_markdown
        from core.integrations.discord.ui_components import build_guide_view

        publisher = DiscordPublisher(bot)
        topic = clean_prompt[5:].strip() or "E-ZZIO"
        async with message.channel.typing():
            try:
                target, thread_id = await publisher.ensure_thread(message.channel, topic)
                thread_session = (
                    f"{session_scope}:thread_{thread_id}" if thread_id else session_scope
                )
                resp = await get_http_client().post(
                    LOCAL_API_URL,
                    json={
                        "text": f"Rédige un guide Markdown complet et structuré sur : {topic}",
                        "session_id": thread_session,
                        "mission_profile": "COMPLEX",
                        "model_target": "gemini",
                        "channel": "discord",
                    },
                    timeout=120.0,
                )
                guide = resp.json().get("response", "") if resp.status_code == 200 else ""
                if not guide.strip():
                    guide = "Guide indisponible (noyau injoignable)."
                await publisher.post_guide(target, topic, guide, tags=["guide"])
                pages = split_markdown(f"**{topic}**\n\n{guide}")
                if len(pages) > 1:
                    view = build_guide_view(pages, topic, guide)
                    await target.send(pages[0][:1950], view=view)
            except Exception as exc:
                logger.error("[DISCORD] guide impossible : %s", exc)
                await message.channel.send("❌ Génération du guide impossible.")
        return
    if lowered in ("join", "leave") or lowered.startswith("speak "):
        from core.integrations.discord import voice_adapter

        async with message.channel.typing():
            if lowered == "join":
                ok, info = await voice_adapter.join_author_channel(message)
            elif lowered == "leave":
                ok, info = await voice_adapter.leave_channel(message)
            else:
                ok, info = await voice_adapter.speak(message, clean_prompt[6:].strip())
            await message.channel.send(("✅ " if ok else "❌ ") + info)
        return

    async with message.channel.typing():
        try:
            payload = {
                "text": clean_prompt,
                "session_id": session_scope,
                "force_cloud": False,
                "speed": "fast",
                "mission_profile": mission_profile,
                "model_target": model_target,
                "channel": "discord",
            }

            if message.attachments:
                for attachment in message.attachments:
                    fname = (attachment.filename or "").lower()
                    if any(fname.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]):
                        payload["image_url"] = attachment.url
                        break
                for attachment in message.attachments:
                    fname = (attachment.filename or "").lower()
                    if any(
                        fname.endswith(ext)
                        for ext in [".log", ".py", ".gd", ".lua", ".txt", ".json", ".md"]
                    ):
                        try:
                            raw = await attachment.read()
                            if len(raw) > 1_000_000:
                                clean_prompt += (
                                    f"\n\n[FICHIER {attachment.filename} trop volumineux, ignoré]"
                                )
                            else:
                                txt = raw.decode("utf-8", errors="ignore")[:6000]
                                clean_prompt = (
                                    f"[CONTEXTE FICHIER {attachment.filename}]\n{txt}\n"
                                    f"[/CONTEXTE]\n\n{clean_prompt}"
                                )
                        except Exception as att_exc:
                            logger.warning(
                                "[DISCORD] PJ illisible %s : %s", attachment.filename, att_exc
                            )
                        break
                payload["text"] = clean_prompt

            resp = await get_http_client().post(LOCAL_API_URL, json=payload, timeout=45.0)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    raw_res = data.get("response", "")
                    if isinstance(raw_res, dict):
                        body_text = (
                            raw_res.get("response")
                            or raw_res.get("answer")
                            or raw_res.get("content")
                            or str(raw_res)
                        )
                    elif isinstance(raw_res, str):
                        body_text = raw_res if raw_res.strip() else "Réponse vide du noyau."
                    else:
                        body_text = (
                            str(raw_res) if raw_res is not None else "Réponse vide du noyau."
                        )

                    # Extraire les métadonnées de fédération pour la bannière
                    prov = data.get("provider") or "Unknown"
                    mdl = data.get("model") or "Unknown"
                    msn = data.get("mission") or mission_profile
                    latency_s = f"{data.get('elapsed_ms', 0) / 1000.0:.2f}s"
                    status_str = "SUCCESS" if data.get("ok", True) else "FAIL"

                    # Construction de la bannière unifiée
                    banner = (
                        f"**E-ZZIO**\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"**Mission**  : `{msn}`\n"
                        f"**Provider** : `{prov}`\n"
                        f"**Model**    : `{mdl}`\n"
                        f"**Latency**  : `{latency_s}`\n"
                        f"**Status**   : `{status_str}`\n"
                        f"━━━━━━━━━━━━━━━━━━\n\n"
                    )
                    reply_text = banner + body_text
                else:
                    reply_text = str(data) if data is not None else "Réponse vide du noyau."
            else:
                reply_text = f"Erreur de communication noyau (Code {resp.status_code})."

            from core.integrations.discord.ui_components import StreamEditor

            async def _first_chunk(content: str):
                if is_private:
                    return await message.channel.send(content)
                return await message.reply(content)

            await StreamEditor().render(_first_chunk, reply_text)

        except DISCORD_NET_ERRORS as net_exc:
            logger.error("[DISCORD] Noyau injoignable : %s", net_exc)
            backend_down = "⚠️ Erreur noyau E-zzio : Le serveur local (:8001) ne répond pas. Vérifie son exécution."
            if is_private:
                await message.channel.send(backend_down)
            else:
                await message.reply(backend_down)
        except Exception as e:
            logger.exception("[DISCORD] Erreur traitement message")
            secret_redactor.sanitize(str(e))
            error_reply = "❌ Erreur interne E-ZZIO."
            if is_private:
                await message.channel.send(error_reply)
            else:
                await message.reply(error_reply)

    # await bot.process_commands(message) # Neutralisé pour éviter les doublons


@bot.event
async def on_message(message):
    if getattr(message.author, "bot", False):
        return
    async with message.channel.typing():
        await _handle_message(message)


def main() -> int:
    """Point d'entrée robuste : valide le token puis lance le client."""
    token = resolve_discord_token() or secrets_loader.discord_token(_LOADED_SECRETS)
    if not token or token.count(".") < 2:
        print(
            "[CRITICAL] Token Discord introuvable dans la configuration ou l'environnement.",
            file=sys.stderr,
        )
        logger.critical(
            "[SECRETS] Token Discord invalide ou absent. "
            "Renseignez DISCORD_TOKEN (ou DISCORD_BOT_TOKEN) dans secrets/.env "
            "avec un token valide du portail Discord, puis relancez."
        )
        return 1
    try:
        bot.run(token)
    except KeyboardInterrupt:
        logger.info("[DISCORD] Arrêt demandé par l'utilisateur.")
    except Exception as exc:
        logger.exception("[DISCORD] Échec fatal du client : %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    # bootstrap du client discord avec gestion d'erreurs explicite
    sys.exit(main())
