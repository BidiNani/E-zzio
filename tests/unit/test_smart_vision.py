"""Tests pour core/smart_vision.py.

Module 100% stdlib (base64, json, urllib, pathlib). L'appel à Ollama
se fait via urllib.request.urlopen → mockable.

Découvertes pré-test :
- OLLAMA_URL peut être mal formé si OLLAMA_HOST n'a pas de scheme
  → on le monkeypatch dans les tests
- save_upload garde les "." donc ".." survit (mais préfixé par "smart_")
  → test adapté pour vérifier l'absence de path traversal réel
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core import smart_vision

# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def fake_image(tmp_path):
    """Petite image PNG factice (bytes)."""
    png_bytes = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000d49444154789c6300010000000500010d0a2db40000000049454e44ae426082"
    )
    p = tmp_path / "test.png"
    p.write_bytes(png_bytes)
    return p


@pytest.fixture
def fix_ollama_url(monkeypatch):
    """Force OLLAMA_URL à une valeur valide pour urllib."""
    monkeypatch.setattr(smart_vision, "OLLAMA_URL", "http://127.0.0.1:11434")
    return "http://127.0.0.1:11434"


# ============================================================
# 1. Smoke + constantes
# ============================================================

class TestSmoke:
    def test_module_imports(self):
        assert smart_vision is not None

    def test_constants(self):
        assert smart_vision.VISION_MODEL
        assert smart_vision.OLLAMA_URL
        assert smart_vision.PROJECT_ROOT is not None

    def test_tech_words_list(self):
        assert "powershell" in smart_vision.TECH_WORDS
        assert "error" in smart_vision.TECH_WORDS

    def test_logo_words_list(self):
        assert "logo" in smart_vision.LOGO_WORDS
        assert "illustration" in smart_vision.LOGO_WORDS


# ============================================================
# 2. _b64
# ============================================================

class TestB64:
    def test_encodes_file(self, fake_image):
        result = smart_vision._b64(fake_image)
        assert isinstance(result, str)
        decoded = base64.b64decode(result)
        assert decoded == fake_image.read_bytes()

    def test_raises_on_missing(self, tmp_path):
        missing = tmp_path / "nope.png"
        with pytest.raises(FileNotFoundError):
            smart_vision._b64(missing)


# ============================================================
# 3. infer_kind — fonction pure
# ============================================================

class TestInferKind:
    def test_technical_screenshot_from_filename(self):
        result = smart_vision.infer_kind("screenshot_error.png", "")
        assert result["kind"] == "technical_screenshot"
        assert result["technical"] is True

    def test_technical_from_prompt(self):
        result = smart_vision.infer_kind("image.png", "corrige ce traceback python")
        assert result["kind"] == "technical_screenshot"

    def test_logo_from_filename(self):
        result = smart_vision.infer_kind("logo_druide.png", "")
        assert result["kind"] == "logo_or_illustration"
        assert result["logo_or_illustration"] is True

    def test_logo_from_prompt(self):
        result = smart_vision.infer_kind("x.png", "decris cette illustration")
        assert result["kind"] == "logo_or_illustration"

    def test_visual_description_default(self):
        result = smart_vision.infer_kind("photo.jpg", "décris la scène")
        assert result["kind"] == "visual_description"
        assert result["technical"] is False
        assert result["logo_or_illustration"] is False

    def test_technical_wins_over_logo(self):
        result = smart_vision.infer_kind("logo_powershell.png", "")
        assert result["kind"] == "technical_screenshot"

    def test_empty_inputs(self):
        result = smart_vision.infer_kind()
        assert result["kind"] == "visual_description"


# ============================================================
# 4. build_prompt — fonction pure
# ============================================================

class TestBuildPrompt:
    def test_returns_string(self):
        result = smart_vision.build_prompt("test.png", "")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_common_section(self):
        result = smart_vision.build_prompt("x.png", "")
        assert "E-ZZIO" in result
        assert "francais" in result

    def test_technical_mode(self):
        result = smart_vision.build_prompt("error.png", "")
        assert "technique" in result.lower()

    def test_logo_mode(self):
        result = smart_vision.build_prompt("logo.png", "")
        assert "logo" in result.lower()
        assert "couleurs" in result.lower()

    def test_general_mode(self):
        result = smart_vision.build_prompt("photo.jpg", "")
        assert "image" in result.lower()

    def test_includes_user_prompt(self):
        result = smart_vision.build_prompt("x.png", "Ma demande perso")
        assert "Ma demande perso" in result

    def test_default_prompt_when_empty(self):
        result = smart_vision.build_prompt("x.png", "")
        assert "decris" in result.lower() or "décris" in result.lower()


# ============================================================
# 5. clean_reply — fonction pure
# ============================================================

class TestCleanReply:
    def test_empty_reply(self):
        result = smart_vision.clean_reply("")
        assert "pas obtenu" in result.lower() or "essaie" in result.lower()

    def test_whitespace_only(self):
        result = smart_vision.clean_reply("   \n  ")
        assert "pas obtenu" in result.lower() or "essaie" in result.lower()

    def test_technical_reply_preserved(self):
        reply = "1. Erreur détectée\n2. Correction PowerShell : fais ceci\n3. Test : lance ça"
        result = smart_vision.clean_reply(reply, "error.png", "")
        assert "Erreur" in result

    def test_logo_strips_powershell(self):
        reply = """
1. Description : c'est un logo violet
2. Correction PowerShell : lance cette commande
3. Test de validation : vérifie le résultat
"""
        result = smart_vision.clean_reply(reply, "logo.png", "")
        assert "Correction PowerShell" not in result
        assert "Test de validation" not in result

    def test_logo_short_reply_gets_replaced(self):
        reply = "C'est un logo."
        result = smart_vision.clean_reply(reply, "logo.png", "")
        assert len(result) > len(reply)

    def test_logo_specific_bad_text_replaced(self):
        reply = "On voit des éléments graphiques complexes dans cette image."
        result = smart_vision.clean_reply(reply, "logo.png", "")
        assert "éléments graphiques complexes" not in result.lower()

    def test_general_mode_no_strip(self):
        reply = "Description normale avec des mots simples."
        result = smart_vision.clean_reply(reply, "photo.jpg", "")
        assert "normale" in result


# ============================================================
# 6. ollama_vision — mock urllib (OLLAMA_URL fixé)
# ============================================================

class TestOllamaVision:
    def test_success(self, fake_image, fix_ollama_url):
        """Mock urlopen → retourne dict avec ok=True."""
        fake_response = MagicMock()
        fake_response.read.return_value = json.dumps({
            "response": "Description de l'image",
            "model": "qwen2.5vl:3b",
        }).encode("utf-8")
        fake_response.__enter__ = MagicMock(return_value=fake_response)
        fake_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=fake_response):
            result = smart_vision.ollama_vision(fake_image, "test prompt")
            assert result["ok"] is True
            assert result["reply"] == "Description de l'image"

    def test_network_error_propagates(self, fake_image, fix_ollama_url):
        """Si urlopen lève → l'exception remonte."""
        with patch("urllib.request.urlopen", side_effect=ConnectionError("boom")):
            with pytest.raises(ConnectionError):
                smart_vision.ollama_vision(fake_image, "test")


# ============================================================
# 7. analyze_path — orchestrateur
# ============================================================

class TestAnalyzePath:
    def test_missing_file(self, tmp_path):
        missing = tmp_path / "nope.png"
        result = smart_vision.analyze_path(str(missing))
        assert result["ok"] is False
        assert "introuvable" in result["error"].lower()

    def test_success_with_mocked_ollama(self, fake_image):
        with patch.object(
            smart_vision, "ollama_vision",
            return_value={"ok": True, "model": "qwen2.5vl:3b", "reply": "Belle image."}
        ):
            result = smart_vision.analyze_path(str(fake_image))
            assert result["ok"] is True
            assert result["kind"] in ("visual_description", "technical_screenshot", "logo_or_illustration")
            assert "policy" in result
            assert result["policy"]["gpu"] == "untouched"

    def test_error_from_ollama(self, fake_image):
        with patch.object(
            smart_vision, "ollama_vision",
            side_effect=RuntimeError("api down")
        ):
            result = smart_vision.analyze_path(str(fake_image))
            assert result["ok"] is False
            assert "api down" in result["error"]


# ============================================================
# 8. save_upload
# ============================================================

class TestSaveUpload:
    def test_saves_file(self, monkeypatch, tmp_path):
        monkeypatch.setattr(smart_vision, "INBOX", tmp_path)
        p = smart_vision.save_upload("test.png", b"fake content")
        assert p.exists()
        assert p.read_bytes() == b"fake content"

    def test_prefix_prevents_path_traversal(self, monkeypatch, tmp_path):
        """Le préfixe 'smart_<timestamp>_' noie le '..' → pas de path traversal."""
        monkeypatch.setattr(smart_vision, "INBOX", tmp_path)
        p = smart_vision.save_upload("../../etc/passwd", b"x")
        # Le fichier reste dans tmp_path (pas de traversal)
        assert p.parent == tmp_path
        # Le nom contient le préfixe smart_ + timestamp
        assert p.name.startswith("smart_")

    def test_default_filename(self, monkeypatch, tmp_path):
        monkeypatch.setattr(smart_vision, "INBOX", tmp_path)
        p = smart_vision.save_upload("", b"x")
        assert "image.png" in p.name
