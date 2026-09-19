import pytest
import time
from v17.channels.discord_adapter import (
    discord_channel_adapter,
    DiscordInboundMessage,
    DISCORD_MAX_MESSAGE_LEN
)

def test_v17_6d_discord_identity_and_basic_chat():
    msg = DiscordInboundMessage(
        message_id="msg_101",
        channel_id="chan_gen",
        guild_id="guild_main",
        author_id="user_42",
        author_name="Alice",
        content="Bonjour E-ZZIO",
        timestamp=time.time()
    )
    res = discord_channel_adapter.process_inbound_message(msg)
    assert res.message_id == "msg_101"
    assert res.session_id == "discord_guild_main_chan_gen_user_42"
    assert res.verified is True
    assert len(res.chunks) == 1
    assert "E-zzio" in res.chunks[0]

def test_v17_6d_discord_model_routing_powershell_code():
    msg = DiscordInboundMessage(
        message_id="msg_102",
        channel_id="chan_dev",
        guild_id="guild_main",
        author_id="user_42",
        author_name="Alice",
        content="Analyse ce script powershell pour moi",
        timestamp=time.time()
    )
    res = discord_channel_adapter.process_inbound_message(msg)
    assert res.task_type in ["POWERSHELL", "CODE"]
    assert res.selected_model == "qwen2.5-coder:14b"

def test_v17_6d_discord_mention_suppression():
    msg = DiscordInboundMessage(
        message_id="msg_103",
        channel_id="chan_gen",
        author_id="user_99",
        author_name="Bob",
        content="Hello @everyone et @here",
        timestamp=time.time()
    )
    res = discord_channel_adapter.process_inbound_message(msg)
    for c in res.chunks:
        assert "@everyone" not in c
        assert "@here" not in c

def test_v17_6d_discord_long_response_chunking():
    msg = DiscordInboundMessage(
        message_id="msg_104",
        channel_id="chan_gen",
        author_id="user_99",
        author_name="Bob",
        content="A" * 3000,
        timestamp=time.time()
    )
    res = discord_channel_adapter.process_inbound_message(msg)
    assert len(res.chunks) >= 2
    for chunk in res.chunks:
        assert len(chunk) <= DISCORD_MAX_MESSAGE_LEN

def test_v17_6d_discord_human_approval_gate_for_critical():
    msg = DiscordInboundMessage(
        message_id="msg_105",
        channel_id="chan_admin",
        author_id="user_admin",
        author_name="Admin",
        content="Supprime et purge toutes les données de session",
        timestamp=time.time()
    )
    res = discord_channel_adapter.process_inbound_message(msg)
    assert "Action Soumise à Validation" in res.chunks[0]
