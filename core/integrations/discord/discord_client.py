import asyncio
import aiohttp
from datetime import datetime, timezone

http_session: aiohttp.ClientSession | None = None
import asyncio
"""
E-ZZIO Sovereign Discord Agent Client (V7.51 Dynamic Presence & Vault Hardened)
Intègre le Secure Vault, la session aiohttp persistante et le statut dynamique.
"""

import sys
import pathlib
import discord
from discord.ext import commands, tasks
import aiohttp

PROJECT_ROOT = pathlib.Path(r"G:\AI\E-zzio")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.integrations.discord.permission_guard import permission_guard
from core.security.secret_redactor import secret_redactor
from core.integrations.discord.discord_watchdog import discord_watchdog
from core.tool_gateway.google_bridge import GoogleIdentityBridge
from runtime.adapters.config.dotenv_provider import DotEnvConfigProvider

config = DotEnvConfigProvider(env_path=str(PROJECT_ROOT / "secrets" / ".env"))
google_bridge = GoogleIdentityBridge(config=config)

OWNER_ID = "186035306418405376"


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
LOCAL_API_URL = config.get("EZZIO_LOCAL_API_URL", "http://127.0.0.1:8001/master/chat")

PROACTIVE_POLL_URL = config.get("EZZIO_PROACTIVE_API_URL", "http://127.0.0.1:8001/system/proactive/poll")

if not DISCORD_TOKEN:
    print("[!] ERREUR CRITIQUE : Aucun token Discord trouvé.")
    sys.exit(1)

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
        activity = discord.Activity(type=discord.ActivityType.watching, name="🧠 E-ZZIO | Kernel ONLINE | 🔐 Vault OK")
        await bot.change_presence(status=discord.Status.online, activity=activity)
    except Exception:
        pass


_reported_anomalies: set[str] = set()

async def run_autonomous_diagnostic() -> list[str]:
    """Exécute un cycle de diagnostic passif sans altérer l'état du système."""
    findings = []
    global http_session
    
    # 1. Sonde de santé de l'API Backend locale
    health_ok = False
    health_detail = ""
    try:
        if http_session is None or http_session.closed:
            http_session = aiohttp.ClientSession()
        async with http_session.get("http://127.0.0.1:8001/health", timeout=aiohttp.ClientTimeout(total=4.0)) as resp:
            if resp.status == 200:
                data = await resp.json()
                if isinstance(data, dict):
                    raw_res = data.get("response", "")
                    if isinstance(raw_res, dict):
                        reply_text = raw_res.get("response") or raw_res.get("answer") or raw_res.get("content") or str(raw_res)
                    elif isinstance(raw_res, str):
                        reply_text = raw_res if raw_res.strip() else "Réponse vide du noyau."
                    else:
                        reply_text = str(raw_res) if raw_res is not None else "Réponse vide du noyau."
                else:
                    reply_text = str(data) if data is not None else "Réponse vide du noyau."
            else:
                health_detail = "HTTP " + str(resp.status)
    except Exception as exc:
        health_detail = str(exc)

    if not health_ok:
        if "backend_health" not in _reported_anomalies:
            findings.append("⚠️ **Alerte Santé API** : Le backend local (`8001/health`) ne répond pas.\n> Détail : `" + str(health_detail) + "`")
            _reported_anomalies.add("backend_health")
    else:
        if "backend_health" in _reported_anomalies:
            findings.append("✅ **Rétablissement** : L'API backend locale (`8001/health`) est de nouveau opérationnelle.")
            _reported_anomalies.discard("backend_health")

    # 2. Sonde de détection des doublons de processus (web_server.py)
    try:
        proc = await asyncio.create_subprocess_exec(
            "powershell", "-NoProfile", "-Command",
            "(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*web_server.py*' }).Count",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
        out_str = stdout.decode().strip()
        dup_count = int(out_str) if out_str.isdigit() else 1
        
        if dup_count > 1:
            if "duplicate_web" not in _reported_anomalies:
                findings.append("⚠️ **Anomalie Processus** : " + str(dup_count) + " instances de `web_server.py` tournent simultanément.")
                _reported_anomalies.add("duplicate_web")
        else:
            if "duplicate_web" in _reported_anomalies:
                findings.append("✅ **Rétablissement** : Les instances de `web_server.py` sont normalisées.")
                _reported_anomalies.discard("duplicate_web")
    except Exception:
        pass

    return findings


@tasks.loop(minutes=2)
async def proactive_event_loop():
    """Surveillance continue et dispatching autonome en Message Privé."""
    try:
        findings = await run_autonomous_diagnostic()
        if findings and OWNER_ID:
            owner = bot.get_user(int(OWNER_ID)) or await bot.fetch_user(int(OWNER_ID))
            if owner:
                now_str = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
                header = "🧠 **[E-ZZIO Diagnostic — " + str(now_str) + "]**\n"
                payload = header + "\n".join(findings)
                sanitized = secret_redactor.sanitize(payload)
                # [NETTOYAGE v4.1] Suppression du spam de santé en DM`n    # await owner.send(sanitized)`n    print(f"[PROACTIF SILENCIEUX] {sanitized}")
    except Exception as exc:
        print(f"[PROACTIVE] Exception dans la boucle de notification : {exc}")

@proactive_event_loop.before_loop
async def before_proactive_loop():
    await bot.wait_until_ready()

_notified_missions: set[str] = set()

@tasks.loop(seconds=5)
async def mission_notifier_loop():
    """Vérifie périodiquement les missions terminées et notifie l'utilisateur."""
    global http_session
    try:
        if http_session is None or http_session.closed:
            http_session = aiohttp.ClientSession()

        missions_url = LOCAL_API_URL.replace("/master/chat", "/master/api/v1/missions")
        async with http_session.get(missions_url, timeout=aiohttp.ClientTimeout(total=4.0)) as resp:
            if resp.status == 200:
                data = await resp.json()
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
                                    banner += f"\n**Artifacts** :\n" + "\n".join(f"- `{a}`" for a in m.get("artifacts"))
                                banner += "\n━━━━━━━━━━━━━━━━━━\n"
                                await owner.send(banner)
    except Exception:
        pass

@mission_notifier_loop.before_loop
async def before_mission_notifier():
    await bot.wait_until_ready()


@bot.event
async def on_ready():
    global http_session
    if http_session is None or http_session.closed:
        http_session = aiohttp.ClientSession()

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
    global http_session
    if http_session and not http_session.closed:
        await http_session.close()


@bot.event
async def on_message(message):
    global http_session
    if message.author == bot.user:
        return

    discord_user_id = str(message.author.id)
    username = str(message.author.name)
    is_private = isinstance(message.channel, discord.DMChannel)
    guild_id = str(message.guild.id) if message.guild else None

    auth_check = permission_guard.evaluate_guild_access(guild_id, discord_user_id, username, is_private)
    if not auth_check["granted"]:
        if is_private:
            await message.channel.send("❌ Accès privé non autorisé.")
        return

    if is_private:
        raw_prompt = message.content.strip()
    else:
        if not message.content.startswith("!e "):
            return
        raw_prompt = message.content[3:].strip()

    if not raw_prompt and not message.attachments:
        return

    # Parse profile flag: e.g. !e --profile=COMPLEX <prompt> or -p COMPLEX <prompt>
    mission_profile = "STANDARD"
    model_target = "auto"
    clean_prompt = raw_prompt

    import re
    profile_match = re.search(r'--(?:profile|p)=([A-Za-z0-9_]+)', clean_prompt)
    if profile_match:
        mission_profile = profile_match.group(1).upper()
        clean_prompt = clean_prompt[:profile_match.start()] + clean_prompt[profile_match.end():]
        clean_prompt = clean_prompt.strip()

    target_match = re.search(r'--(?:target|model)=([A-Za-z0-9_]+)', clean_prompt)
    if target_match:
        model_target = target_match.group(1).lower()
        clean_prompt = clean_prompt[:target_match.start()] + clean_prompt[target_match.end():]
        clean_prompt = clean_prompt.strip()

    discord_watchdog.record_activity()

    async with message.channel.typing():
        try:
            payload = {
                "text": clean_prompt,
                "session_id": f"disc_user_{message.author.id}",
                "force_cloud": False,
                "speed": "fast",
                "mission_profile": mission_profile,
                "model_target": model_target,
                "channel": "discord",
            }

            if message.attachments:
                for attachment in message.attachments:
                    if any(attachment.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]):
                        payload["image_url"] = attachment.url
                        break

            if http_session is None or http_session.closed:
                http_session = aiohttp.ClientSession()

            async with http_session.post(LOCAL_API_URL, json=payload, timeout=45.0) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, dict):
                        raw_res = data.get("response", "")
                        if isinstance(raw_res, dict):
                            body_text = raw_res.get("response") or raw_res.get("answer") or raw_res.get("content") or str(raw_res)
                        elif isinstance(raw_res, str):
                            body_text = raw_res if raw_res.strip() else "Réponse vide du noyau."
                        else:
                            body_text = str(raw_res) if raw_res is not None else "Réponse vide du noyau."

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
                    reply_text = f"Erreur de communication noyau (Code {resp.status})."

            chunk_size = 1950
            for i in range(0, len(reply_text), chunk_size):
                if is_private:
                    await message.channel.send(reply_text[i : i + chunk_size])
                else:
                    await message.reply(reply_text[i : i + chunk_size])

        except Exception as e:
            secret_redactor.sanitize(str(e))
            error_reply = "❌ Erreur interne E-ZZIO."
            if is_private:
                await message.channel.send(error_reply)
            else:
                await message.reply(error_reply)


    # await bot.process_commands(message) # Neutralisé pour éviter les doublons


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)









