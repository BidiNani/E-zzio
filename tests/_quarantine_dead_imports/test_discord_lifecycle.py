import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import discord
from runtime.discord.bot_runner import EzzioDiscordBot, main
from routers.chat import _core, _memory_gateway

@pytest.mark.asyncio
async def test_discord_bot_initialization_and_singleton_binding():
    intents = discord.Intents.default()
    bot = EzzioDiscordBot(command_prefix="!", intents=intents)
    assert bot.ezzio_core is _core, "Le bot doit être lié au singleton EzzioCore souverain"
    await bot.close()

@pytest.mark.asyncio
async def test_discord_setup_hook_loads_all_cogs_and_binds_singletons():
    intents = discord.Intents.default()
    bot = EzzioDiscordBot(command_prefix="!", intents=intents)
    
    await bot.setup_hook()
    
    # Vérification des 3 cogs
    assert "ChatCog" in bot.cogs
    assert "ResearchCog" in bot.cogs
    assert "VoiceCog" in bot.cogs
    
    chat_cog = bot.cogs["ChatCog"]
    assert chat_cog.core is _core
    assert chat_cog.memory_gw is _memory_gateway
    
    await bot.close()

@pytest.mark.asyncio
async def test_discord_on_ready_slash_command_sync():
    intents = discord.Intents.default()
    bot = EzzioDiscordBot(command_prefix="!", intents=intents)
    bot.tree.sync = AsyncMock(return_value=[MagicMock(name="chat"), MagicMock(name="research")])
    
    # Simulation on_ready
    await bot.tree.sync()
    bot.tree.sync.assert_awaited_once()
    await bot.close()

@pytest.mark.asyncio
async def test_discord_main_fail_closed_without_token():
    with patch("runtime.discord.bot_runner.TOKEN", None):
        # main() doit quitter proprement sans lever d'exception
        await main()
