"""Tests UI Discord : pagination, export, extraction code, StreamEditor."""
import asyncio

from core.integrations.discord.ui_components import (
    StreamEditor,
    build_guide_view,
    extract_code_blocks,
    progressive_plan,
)


def test_progressive_plan_first_paint():
    snaps = progressive_plan("x" * 5000)
    assert len(snaps[0]) > 20
    assert snaps[-1] == "x" * 5000
    assert all(len(b) > len(a) for a, b in zip(snaps, snaps[1:]))


def test_extract_code_blocks():
    md = "txt\n```python\na = 1\n```\nmid\n```\nb = 2\n```"
    out = extract_code_blocks(md)
    assert "a = 1" in out and "b = 2" in out
    assert extract_code_blocks("rien") == "_Aucun bloc de code._"


def test_stream_editor_throttled_render():
    edits = []

    class FakeMsg:
        async def edit(self, content=None):
            edits.append(content)

    async def fake_send(content):
        return FakeMsg()

    async def run():
        await StreamEditor(interval=0).render(fake_send, "y" * 3000)

    asyncio.run(run())
    assert len(edits) >= 2
    assert edits[-1] == "y" * 1950


def test_guide_view_buttons():
    import discord

    async def run():
        assert issubclass(discord.ui.View, object)
        view = build_guide_view(["p1", "p2"], "T", "# T\nfull")
        return [c.label for c in view.children]

    labels = asyncio.run(run())
    assert labels == ["⬅ Précédent", "Suivant ➡", "💾 Exporter .md", "💻 Extraire Code"]
