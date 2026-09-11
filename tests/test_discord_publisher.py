"""Tests DiscordPublisher : découpage Markdown sûr."""
import asyncio

from core.integrations.discord.publisher import DiscordPublisher, split_markdown


def test_short_text_single_chunk():
    assert split_markdown("Bonjour.") == ["Bonjour."]


def test_paragraph_split_under_limit():
    parts = split_markdown("A\n\n" + "x" * 1200 + "\n\n" + "y" * 1200 + "\n\nB")
    assert all(len(p) <= 1950 for p in parts)
    assert len(parts) >= 2


def test_code_fence_never_split():
    code = "```python\n" + "y = 1\n" * 300 + "```"
    parts = split_markdown("Intro\n\n" + code + "\n\nFin")
    for p in parts:
        assert p.count("```") % 2 == 0, "fence coupé"
    assert all(len(p) <= 1950 for p in parts)


def test_post_guide_sequential():
    sent = []

    class FakeChannel:
        async def reply(self, t):
            sent.append(("reply", t))

        async def send(self, t):
            sent.append(("send", t))

    async def run():
        pub = DiscordPublisher()
        res = await pub.post_guide(FakeChannel(), "T", "A\n\n" + "z" * 4000)
        return res

    res = asyncio.run(run())
    assert res["ok"] is True and res["chunks"] == len(sent) >= 2
    assert all(len(t) <= 1950 for _, t in sent)
