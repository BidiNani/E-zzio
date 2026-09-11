"""Chargeur de secrets : nettoyage, typage, replis, diagnostics masqués."""
from core.config.secrets_loader import (
    discord_owner_id,
    discord_token,
    gemini_keys,
    groq_key,
)


def test_strip_spaces_and_quotes():
    assert discord_token({"DISCORD_TOKEN": '  "abc.def.ghi"  '}) == "abc.def.ghi"
    assert discord_token({"DISCORD_BOT_TOKEN": "  xyz.uvw.rst '"}) == "xyz.uvw.rst"
    assert discord_token({"DISCORD_TOKEN": "  spaced  .  ok  .  yes  "}) == "spaced  .  ok  .  yes"


def test_owner_id_int():
    assert discord_owner_id({"DISCORD_OWNER_ID": " 186035306418405376 "}) == 186035306418405376
    assert discord_owner_id({}) is None
    assert discord_owner_id({"DISCORD_OWNER_ID": "not-an-int"}) is None


def test_malformed_token_rejected():
    assert discord_token({"DISCORD_TOKEN": "abc"}) == ""
    assert discord_token({"DISCORD_TOKEN": "one.two"}) == ""
    assert discord_token({}) == ""


def test_groq_fallback():
    assert groq_key({"GROQ_API_KEY": "g1"}) == "g1"
    assert groq_key({"DISCORD_GROQ_API_KEY": "gd", "GROQ_API_KEY": "g1"}) == "gd"
    assert groq_key({"GROQ_API_KEY_2": "g2"}) == "g2"
    assert groq_key({}) == ""
