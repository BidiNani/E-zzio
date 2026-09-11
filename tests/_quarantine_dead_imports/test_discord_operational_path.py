import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from runtime.discord.bot_runner import EzzioDiscordBot
import discord

@pytest.mark.asyncio
async def test_discord_operational_startup_and_cogs():
    intents = discord.Intents.default()
    intents.message_content = True
    bot = EzzioDiscordBot(command_prefix="!", intents=intents)
    
    # 1. Setup hook nominal
    await bot.setup_hook()
    assert len(bot.extensions) == 3
    assert "runtime.discord.cogs.chat" in bot.extensions
    assert "runtime.discord.cogs.research" in bot.extensions
    assert "runtime.discord.cogs.voice" in bot.extensions

@pytest.mark.asyncio
async def test_discord_operational_command_execution():
    intents = discord.Intents.default()
    bot = EzzioDiscordBot(command_prefix="!", intents=intents)
    await bot.setup_hook()
    
    # Mock de l'interaction slash command /chat
    mock_interaction = MagicMock()
    mock_interaction.user.id = 12345
    mock_interaction.response.defer = AsyncMock()
    mock_interaction.followup.send = AsyncMock()
    
    # Récupération de la commande /chat enregistrée
    chat_cog = bot.get_cog("ChatCog")
    assert chat_cog is not None
    
    mock_think_ret = {
        "response": "Réponse opérationnelle Discord.",
        "intent": "chat",
        "provider": "ollama"
    }
    with patch.object(bot.ezzio_core, "think", new_callable=AsyncMock) as mock_think:
        mock_think.return_value = mock_think_ret
        # Exécution de la commande
        await chat_cog.chat.callback(chat_cog, mock_interaction, message="Hello Ezzio")
    
    mock_interaction.response.defer.assert_awaited_once()
    mock_interaction.followup.send.assert_awaited_once()
    embed = mock_interaction.followup.send.call_args.kwargs.get("embed")
    assert embed is not None
    assert "Réponse opérationnelle Discord." in embed.description

@pytest.mark.asyncio
async def test_discord_operational_clean_shutdown():
    intents = discord.Intents.default()
    bot = EzzioDiscordBot(command_prefix="!", intents=intents)
    await bot.setup_hook()
    
    # Fermeture propre
    await bot.close()
    assert bot.is_closed()
