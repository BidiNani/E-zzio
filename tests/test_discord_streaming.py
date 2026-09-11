"""Streaming Discord : message unique édité, 0 cascade, 0 free-best."""
import asyncio
import pathlib

SRC = pathlib.Path("core/integrations/discord/discord_client.py").read_text(
    encoding="utf-8")


def test_no_freebest_layer():
    assert "free-best" not in SRC
    assert "_stream_openai_reply" not in SRC
    assert "openai_compat" not in SRC


def test_progressive_render_single_message():
    from core.integrations.discord.ui_components import StreamEditor

    edits = []

    class FakeMsg:
        async def edit(self, content=None):
            edits.append(content)

    async def fake_send(content):
        assert len(content) <= 1950
        return FakeMsg()

    async def run():
        await StreamEditor(interval=0).render(fake_send, "z" * 3000)

    asyncio.run(run())
    assert len(edits) >= 2
    assert edits[-1] == "z" * 1950


def test_no_cascade_senders():
    # un seul on_message + un seul point d'envoi principal par flux
    assert SRC.count("async def on_message") == 1
    assert "process_commands(message)" in SRC  # présent mais neutralisé en commentaire
    assert SRC.count("# await bot.process_commands") >= 1
