"""
E-ZZIO Bidi — Launcher
=======================
Point d'entrée autonome du bot Discord Bidi.

Usage:
    python runtime/bidi/launcher.py

Token: lu depuis secrets/.env (DISCORD_BOT_TOKEN ou DISCORD_TOKEN).
Ce launcher ne contient AUCUNE logique cognitive ni de sécurité.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ezzio.bidi.launcher")

# ── Token resolution (same source as existing bot_runner.py) ──────────────────
def _load_token() -> str:
    """Load Discord token from secrets/.env or environment, fail-closed."""
    # Try loading from secrets/.env
    env_path = ROOT_DIR / "secrets" / ".env"
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=env_path, override=True)
        except ImportError:
            # Manual parse without dotenv
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())

    token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
    if not token or token in ("ton_token_ici", "your_token_here"):
        raise RuntimeError(
            "FAIL-CLOSED: No valid Discord token found.\n"
            "Set DISCORD_BOT_TOKEN in secrets/.env"
        )
    return token


async def main():
    # Instantiate kernel (shared between all requests)
    from ezzio_kernel import OrganismKernel
    from runtime.bidi.ezzio_interface import BidiEzzioInterface
    from runtime.bidi.presence import EzzioDiscordBot, register_slash_commands

    logger.info("[E-ZZIO] Initializing kernel...")
    kernel = OrganismKernel()
    status = kernel.get_organism_status()
    logger.info(f"[E-ZZIO] Kernel status: {status['global_state']} | Ledger: {status['decision_ledger']['status']}")

    if "FAIL_CLOSED" in status["decision_ledger"]["status"]:
        logger.error("[E-ZZIO] FAIL-CLOSED: Ledger integrity check failed. Aborting.")
        return

    # Build interface + bot (shared kernel instance)
    interface = BidiEzzioInterface(kernel=kernel)
    bot = EzzioDiscordBot(interface=interface)
    register_slash_commands(bot)

    token = _load_token()
    logger.info("[E-ZZIO] Starting Discord bot...")
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        logger.error(f"[E-ZZIO] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("[E-ZZIO] Shutting down.")

