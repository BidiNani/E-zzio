"""Tests ingestion PJ Discord : règles de routage texte/code vs images."""
import pytest


TEXT_EXTS = (".log", ".py", ".gd", ".lua", ".txt", ".json", ".md")
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def route_attachment(filename: str) -> str:
    """Miroir de la règle on_message (pur, testable)."""
    fname = (filename or "").lower()
    if any(fname.endswith(e) for e in IMAGE_EXTS):
        return "image_url"
    if any(fname.endswith(e) for e in TEXT_EXTS):
        return "inline_context"
    return "ignored"


@pytest.mark.parametrize("f", ["bug.png", "SHOT.JPG", "a.webp", "x.jpeg"])
def test_images_to_multimodal(f):
    assert route_attachment(f) == "image_url"


@pytest.mark.parametrize("f", ["app.log", "main.py", "a.gd", "b.lua", "n.txt", "d.json", "r.md"])
def test_code_to_context(f):
    assert route_attachment(f) == "inline_context"


def test_other_ignored():
    assert route_attachment("a.exe") == "ignored"
    assert route_attachment("") == "ignored"


def test_context_block_format():
    txt = "print(1)"
    block = f"[CONTEXTE FICHIER main.py]\n{txt}\n[/CONTEXTE]"
    assert len(block) < 6200 and "print(1)" in block


def test_telemetry_header_mandatory():
    from core.integrations.discord.ui_components import format_ezzio_response
    out = format_ezzio_response("hello", "gemini", "gemini-3.6-flash", 2940.0)
    for token in ("E-ZZIO", "STANDARD", "gemini", "gemini-3.6-flash",
                  "2.94s", "SUCCESS", "hello"):
        assert token in out
    out2 = format_ezzio_response("", "ollama", "hermes3:8b", 500.0,
                                 mission="CHAT", status="FAIL")
    assert "CHAT" in out2 and "FAIL" in out2 and "0.50s" in out2
