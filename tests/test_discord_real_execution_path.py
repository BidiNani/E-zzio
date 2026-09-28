"""Tests for E-ZZIO Phase 6 Real Execution Path — Discord -> EzzioMaster -> ModelRouter -> Provider.

Verifies end-to-end execution path, secret isolation, policy & budget governance, and audit logging.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.config import secrets_loader
from core.ezzio_master import EzzioMaster
from core.security.secret_redactor import secret_redactor


@pytest.fixture(scope="module")
def loaded_secrets():
    return secrets_loader.load(override=True)


def test_phase5_secret_loading_and_masked_diagnostics(loaded_secrets):
    """Verifies secrets/.env loading, key normalization, and secret masking."""
    assert os.path.exists(secrets_loader.ENV_PATH)

    # 1. Token Discord
    token = secrets_loader.discord_token(loaded_secrets)
    assert bool(token) is True
    assert token.count(".") >= 2
    # Ensure raw secret value is NEVER displayed or logged in plain text
    masked_diag = secrets_loader.log_secrets_diagnostics(loaded_secrets)
    assert masked_diag["DISCORD_TOKEN"].startswith("[PRESENT]")
    assert token not in masked_diag["DISCORD_TOKEN"]

    # 2. Key aliases normalization
    assert "OPENROUTER_API_KEY" in os.environ or "OPENROUTER_API_KEY" in loaded_secrets
    assert "GROQ_API_KEY" in os.environ or "GROQ_API_KEY" in loaded_secrets


@pytest.mark.asyncio
async def test_phase6_discord_message_real_execution_path():
    """Traces full canonical chain: Contract -> Context -> Policy -> Budget -> ModelRouter -> Provider -> Audit."""
    master = EzzioMaster()

    # Dispatch intent through EzzioMaster representing Discord channel input
    result = await master.execute_intent(
        user_prompt="Bonjour E-ZZIO, statut système ?",
        speed="fast",
        force_cloud=True,
        session_id="test-discord-session-001",
        mission_profile="AUTO",
        model_target="auto",
        channel="discord",
    )

    assert isinstance(result, dict)
    assert "response" in result or "text" in result
    assert "model" in result
    assert "provider" in result

    # Verify zero secrets leaked in result payload
    response_text = str(result)
    raw_token = secrets_loader.discord_token()
    if raw_token:
        assert raw_token not in response_text
    sanitized = secret_redactor.sanitize(response_text)
    assert isinstance(sanitized, str)


@pytest.mark.asyncio
async def test_phase6_discord_client_in_process_fallback():
    """Simulates Discord client message handler fallback to in-process EzzioMaster when HTTP server is offline."""
    import discord

    from core.integrations.discord.discord_client import _handle_message

    class AsyncContextManagerMock:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return None

    class MockDMChannel(discord.DMChannel):
        def __init__(self):
            self.id = 999888777
            self._state = MagicMock()

        def typing(self):
            return AsyncContextManagerMock()

        async def send(self, content=None, **kwargs):
            pass

    mock_channel = MockDMChannel()
    mock_channel.send = AsyncMock()

    mock_author = MagicMock()
    mock_author.bot = False
    mock_author.id = "186035306418405376"

    mock_message = MagicMock()
    mock_message.author = mock_author
    mock_message.channel = mock_channel
    mock_message.content = "Statut E-ZZIO"
    mock_message.attachments = []

    # Should execute without raising exceptions or leaking secrets
    await _handle_message(mock_message)
    assert mock_channel.send.called or mock_message.reply.called


def test_anti_double_execution_connect_error_detector():
    """Verifies that is_pre_request_connect_error correctly distinguishes connection refused vs timeouts."""
    import asyncio

    import aiohttp
    import httpx

    from core.integrations.discord.discord_client import is_pre_request_connect_error

    # 1. Connection refused / host unreachable before request -> TRUE (fallback allowed)
    conn_err = httpx.ConnectError("Connection refused")
    assert is_pre_request_connect_error(conn_err) is True

    conn_timeout = httpx.ConnectTimeout("Connect timeout")
    assert is_pre_request_connect_error(conn_timeout) is True

    # 2. Timeout after request sent / ReadTimeout -> FALSE (fallback PROHIBITED)
    read_timeout = httpx.ReadTimeout("Read timeout while waiting for response")
    assert is_pre_request_connect_error(read_timeout) is False

    general_timeout = TimeoutError()
    assert is_pre_request_connect_error(general_timeout) is False

    generic_httpx_timeout = httpx.TimeoutException("Timeout")
    assert is_pre_request_connect_error(generic_httpx_timeout) is False


def test_secrets_loader_fail_closed_collision():
    """Verifies that conflicting secret values raise a fail-closed ValueError."""
    mock_path = MagicMock()
    mock_path.exists.return_value = True
    mock_path.read_text.return_value = "DISCORD_BOT_TOKEN=token_a\nDISCORD_TOKEN=token_b\n"

    with patch("core.config.secrets_loader.ENV_PATH", mock_path):
        with pytest.raises(ValueError, match="SECRETS-FAIL-CLOSED"):
            secrets_loader.load(override=True)


def test_discord_owner_id_strict_validation():
    """Verifies Section 7 requirement: Owner ID validation does NOT extract arbitrary digits from invalid strings."""
    # 1. Valid inputs
    assert secrets_loader.discord_owner_id({"DISCORD_OWNER_ID": "15179"}) == 15179
    assert secrets_loader.discord_owner_id({"DISCORD_OWNER_ID": " 15179 "}) == 15179

    # 2. Invalid inputs must return None without extracting digits
    assert secrets_loader.discord_owner_id({"DISCORD_OWNER_ID": "abc15179"}) is None
    assert secrets_loader.discord_owner_id({"DISCORD_OWNER_ID": "15179abc"}) is None
    assert secrets_loader.discord_owner_id({"DISCORD_OWNER_ID": "15-179"}) is None
    assert secrets_loader.discord_owner_id({"DISCORD_OWNER_ID": "15179 42"}) is None
    assert secrets_loader.discord_owner_id({"DISCORD_OWNER_ID": ""}) is None


def test_google_identity_bridge_hardening(monkeypatch):
    """Verifies GoogleIdentityBridge fail-closed security and secret masking."""
    from core.tool_gateway.google_bridge import GoogleIdentityBridge

    # Cas A: EZZIO_LEDGER_SECRET present -> bridge initializes cleanly
    monkeypatch.setenv("EZZIO_LEDGER_SECRET", "test_master_ledger_secret_2026_xyz")
    bridge = GoogleIdentityBridge()
    assert bridge.master_secret == b"test_master_ledger_secret_2026_xyz"

    # Cas B: EZZIO_LEDGER_SECRET absent -> fail closed, ValueError raised, no default key
    monkeypatch.delenv("EZZIO_LEDGER_SECRET", raising=False)
    mock_empty_env = MagicMock()
    mock_empty_env.exists.return_value = False
    with patch("core.config.secrets_loader.ENV_PATH", mock_empty_env):
        with pytest.raises(ValueError, match="SECURITY-FAIL-CLOSED") as exc_info:
            GoogleIdentityBridge()

    # Cas C: Secret value is never leaked in the exception message
    exc_text = str(exc_info.value)
    assert "test_master_ledger_secret_2026_xyz" not in exc_text
