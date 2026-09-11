"""Client Discord unifié : 1 listener, filtre bots, typing, pas de doublon."""
import ast
from pathlib import Path

SRC = Path("core/integrations/discord/discord_client.py").read_text(encoding="utf-8")
TREE = ast.parse(SRC)


def _handlers():
    return [n for n in ast.walk(TREE)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.name == "on_message"]


def test_single_on_message_listener():
    assert len(_handlers()) == 1


def test_bot_filter_first():
    src = ast.get_source_segment(SRC, _handlers()[0])
    assert 'getattr(message.author, "bot", False)' in src
    assert src.index("message.author") < src.index("_handle_message")
    assert "typing" in src


def test_no_process_commands_call():
    assert "bot.process_commands(" not in SRC.replace("# await bot.process_commands", "")


def test_typing_before_inference():
    src = ast.get_source_segment(SRC, _handlers()[0])
    assert "message.channel.typing()" in src
    assert src.index("typing") < src.index("_handle_message")


def test_no_cog_registration():
    assert "add_cog" not in SRC
    assert "load_extension" not in SRC
