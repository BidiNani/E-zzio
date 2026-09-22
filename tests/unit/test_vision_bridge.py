"""Tests pour core/vision_bridge.py.

Dépendances : ollama (installé), PIL (12.3.0).

Fonctions pures à tester directement :
- build_vision_prompt(user_prompt, mode)
- clean_prompt_leak(text)
- quality_warnings(text)
- route_vision_result(text)
- status()

Fonctions avec I/O à mocker :
- _safe_vision_path : validation contre des racines fixes
- _image_info : utilise PIL → tester avec une vraie image générée
- analyze_image_file : utilise ollama.chat → mocker
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core import vision_bridge

# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def fake_png(tmp_path):
    """Génère une vraie image PNG 1x1 avec PIL."""
    from PIL import Image

    p = tmp_path / "test.png"
    img = Image.new("RGB", (10, 10), color=(128, 0, 128))
    img.save(p, format="PNG")
    return p


@pytest.fixture
def fake_inbox(monkeypatch, tmp_path):
    """Redirige VISION_INBOX vers tmp_path."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    monkeypatch.setattr(vision_bridge, "VISION_INBOX", inbox)
    return inbox


@pytest.fixture
def fake_out(monkeypatch, tmp_path):
    """Redirige VISION_OUT vers tmp_path."""
    out = tmp_path / "outputs"
    out.mkdir()
    monkeypatch.setattr(vision_bridge, "VISION_OUT", out)
    return out


@pytest.fixture
def fake_allowed_roots(monkeypatch, tmp_path):
    """Redirige toutes les racines autorisées vers tmp_path."""
    monkeypatch.setattr(vision_bridge, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(vision_bridge, "VISION_ROOT", tmp_path / "forge" / "vision")
    monkeypatch.setattr(vision_bridge, "VISION_INBOX", tmp_path / "forge" / "vision" / "inbox")
    monkeypatch.setattr(vision_bridge, "VISION_OUT", tmp_path / "forge" / "vision" / "outputs")
    # Créer les dossiers
    (tmp_path / "forge" / "vision" / "inbox").mkdir(parents=True, exist_ok=True)
    (tmp_path / "forge" / "vision" / "outputs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "workspace").mkdir(parents=True, exist_ok=True)
    return tmp_path


# ============================================================
# 1. Smoke + constantes
# ============================================================

class TestSmoke:
    def test_module_imports(self):
        assert vision_bridge is not None

    def test_constants(self):
        assert vision_bridge.MODEL_VISION == "qwen2.5vl:3b"
        assert vision_bridge.MODEL_FALLBACK_TEXT == "qwen3:1.7b"
        assert vision_bridge.PROJECT_ROOT is not None

    def test_cpu_only_env_forced(self):
        """Le module force CPU_ONLY_ENV à l'import."""
        import os
        assert os.environ.get("OLLAMA_NUM_GPU") == "0"
        assert os.environ.get("EZZIO_GPU_POLICY") == "cpu_ram_only"

    def test_directories_created(self):
        """VISION_INBOX et VISION_OUT existent après import."""
        assert vision_bridge.VISION_INBOX.exists()
        assert vision_bridge.VISION_OUT.exists()


# ============================================================
# 2. build_vision_prompt — fonction pure
# ============================================================

class TestBuildVisionPrompt:
    def test_returns_string(self):
        result = vision_bridge.build_vision_prompt("décris", "auto")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_rules(self):
        result = vision_bridge.build_vision_prompt("", "auto")
        assert "E-ZZIO" in result
        assert "Yeux" in result

    def test_includes_user_prompt(self):
        result = vision_bridge.build_vision_prompt("Ma demande", "auto")
        assert "Ma demande" in result

    def test_default_prompt_when_empty(self):
        result = vision_bridge.build_vision_prompt("", "auto")
        assert "Analyse l'image" in result

    def test_debug_mode(self):
        result = vision_bridge.build_vision_prompt("test", "debug")
        assert "debug" in result.lower()

    def test_ui_mode(self):
        result = vision_bridge.build_vision_prompt("test", "ui")
        assert "interface" in result.lower() or "ui" in result.lower()

    def test_creative_mode(self):
        result = vision_bridge.build_vision_prompt("test", "creative")
        assert "créative" in result.lower() or "creative" in result.lower()

    def test_unknown_mode_falls_back_to_auto(self):
        result = vision_bridge.build_vision_prompt("test", "unknown_mode")
        assert "auto" in result.lower()


# ============================================================
# 3. clean_prompt_leak — fonction pure
# ============================================================

class TestCleanPromptLeak:
    def test_clean_text_preserved(self):
        text = "Voici une analyse visuelle simple."
        assert vision_bridge.clean_prompt_leak(text) == text

    def test_empty(self):
        assert vision_bridge.clean_prompt_leak("") == ""

    def test_none_becomes_empty(self):
        assert vision_bridge.clean_prompt_leak(None) == ""

    def test_strips_leak_after_200_chars(self):
        """Un marker de fuite > 200 chars → coupé."""
        prefix = "A" * 250
        text = prefix + "Règles obligatoires : ne pas faire ceci"
        result = vision_bridge.clean_prompt_leak(text)
        assert "Règles obligatoires" not in result
        assert result.startswith("A")

    def test_leak_before_200_not_stripped(self):
        """Un marker de fuite < 200 chars → non coupé."""
        text = "Règles obligatoires"  # idx=0, pas > 200
        result = vision_bridge.clean_prompt_leak(text)
        assert "Règles obligatoires" in result

    def test_reduces_newlines(self):
        text = "a\n\n\n\n\nb"
        result = vision_bridge.clean_prompt_leak(text)
        assert result == "a\n\nb"


# ============================================================
# 4. quality_warnings — fonction pure
# ============================================================

class TestQualityWarnings:
    def test_clean_text(self):
        assert vision_bridge.quality_warnings("analyse propre") == []

    def test_detects_chmod(self):
        warnings = vision_bridge.quality_warnings("utilise chmod +x script.sh")
        assert len(warnings) >= 1
        assert any("chmod" in w for w in warnings)

    def test_detects_docker(self):
        warnings = vision_bridge.quality_warnings("lance docker compose up")
        assert any("docker" in w for w in warnings)

    def test_detects_pip3(self):
        warnings = vision_bridge.quality_warnings("pip3 install foo")
        assert any("pip3" in w for w in warnings)

    def test_multiple_banned(self):
        text = "chmod 777 && docker run && pip3 install"
        warnings = vision_bridge.quality_warnings(text)
        assert len(warnings) >= 3

    def test_empty(self):
        assert vision_bridge.quality_warnings("") == []

    def test_none(self):
        assert vision_bridge.quality_warnings(None) == []

    def test_case_insensitive(self):
        warnings = vision_bridge.quality_warnings("DOCKER run")
        assert any("docker" in w for w in warnings)


# ============================================================
# 5. route_vision_result — fonction pure
# ============================================================

class TestRouteVisionResult:
    def test_technical_error(self):
        result = vision_bridge.route_vision_result("Une erreur est survenue")
        assert result["next_organ"] == "mains"

    def test_technical_traceback(self):
        result = vision_bridge.route_vision_result("Traceback (most recent call last)")
        assert result["next_organ"] == "mains"

    def test_ui_detected(self):
        result = vision_bridge.route_vision_result("interface utilisateur avec boutons")
        assert result["next_organ"] == "yeux+mains"

    def test_creative_image(self):
        result = vision_bridge.route_vision_result("belle composition visuelle")
        assert result["next_organ"] == "forge"

    def test_default_presence(self):
        result = vision_bridge.route_vision_result("bonjour")
        assert result["next_organ"] == "presence"

    def test_priority_error_over_ui(self):
        """Un texte 'erreur + interface' → error gagne (premier match)."""
        result = vision_bridge.route_vision_result("erreur dans l'interface")
        assert result["next_organ"] == "mains"

    def test_returns_full_dict(self):
        result = vision_bridge.route_vision_result("test")
        assert "next_organ" in result
        assert "reason" in result
        assert "next_action" in result


# ============================================================
# 6. _safe_vision_path — validation
# ============================================================

class TestSafeVisionPath:
    def test_rejects_outside_roots(self, fake_allowed_roots):
        """Un chemin hors des racines autorisées → ValueError."""
        outside = fake_allowed_roots / "outside.txt"
        outside.write_text("x")
        with pytest.raises(ValueError, match="refusée"):
            vision_bridge._safe_vision_path(str(outside))

    def test_accepts_inside_forge_vision(self, fake_allowed_roots, tmp_path):
        """Un chemin dans forge/vision → OK."""
        inside = tmp_path / "forge" / "vision" / "inbox" / "test.png"
        inside.write_bytes(b"\x89PNG\r\n\x1a\n")  # header PNG
        result = vision_bridge._safe_vision_path(str(inside))
        assert result.exists()

    def test_accepts_inside_workspace(self, fake_allowed_roots, tmp_path):
        """Un chemin dans workspace → OK."""
        inside = tmp_path / "workspace" / "test.png"
        inside.write_bytes(b"x")
        result = vision_bridge._safe_vision_path(str(inside))
        assert result.exists()

    def test_rejects_missing_file(self, fake_allowed_roots, tmp_path):
        """Un chemin autorisé mais inexistant → FileNotFoundError."""
        missing = tmp_path / "forge" / "vision" / "inbox" / "nope.png"
        with pytest.raises(FileNotFoundError):
            vision_bridge._safe_vision_path(str(missing))


# ============================================================
# 7. _image_info — utilise PIL
# ============================================================

class TestImageInfo:
    def test_valid_png(self, fake_png):
        """Une vraie image PNG → dict avec format/dimensions."""
        info = vision_bridge._image_info(fake_png)
        assert "error" not in info
        assert info["format"] == "PNG"
        assert info["width"] == 10
        assert info["height"] == 10
        assert info["mode"] == "RGB"

    def test_invalid_file(self, tmp_path):
        """Un fichier non-image → dict avec 'error'."""
        bad = tmp_path / "not_an_image.txt"
        bad.write_text("this is not a PNG")
        info = vision_bridge._image_info(bad)
        assert "error" in info


# ============================================================
# 8. save_upload_bytes
# ============================================================

class TestSaveUploadBytes:
    def test_saves_file(self, fake_allowed_roots):
        """save_upload_bytes écrit dans VISION_INBOX."""
        content = b"fake image content"
        p = vision_bridge.save_upload_bytes("test.png", content)
        assert p.exists()
        assert p.read_bytes() == content
        # Est dans VISION_INBOX
        assert p.parent == vision_bridge.VISION_INBOX

    def test_strips_path_from_filename(self, fake_allowed_roots):
        """Path(filename).name élimine les traversals."""
        p = vision_bridge.save_upload_bytes("../../etc/passwd", b"x")
        # Le chemin est réduit à 'passwd'
        assert "passwd" in p.name
        assert p.parent == vision_bridge.VISION_INBOX


# ============================================================
# 9. analyze_image_file — orchestrateur (mock ollama)
# ============================================================

class TestAnalyzeImageFile:
    def test_invalid_image(self, fake_allowed_roots, tmp_path):
        """Fichier non-image → ok=False."""
        bad = tmp_path / "forge" / "vision" / "inbox" / "bad.png"
        bad.write_text("not an image")
        result = vision_bridge.analyze_image_file(str(bad))
        assert result["ok"] is False
        assert "invalide" in result["error"].lower() or "illisible" in result["error"].lower()

    def test_success_with_mocked_ollama(self, fake_allowed_roots, fake_png):
        """Mock ollama.chat → résultat complet."""
        # Déplacer fake_png dans VISION_INBOX
        target = vision_bridge.VISION_INBOX / "test.png"
        target.write_bytes(fake_png.read_bytes())

        fake_response = {"message": {"content": "Analyse OK"}}
        with patch.object(vision_bridge.ollama, "chat", return_value=fake_response):
            result = vision_bridge.analyze_image_file(str(target))
            assert result["ok"] is True
            assert result["analysis"] == "Analyse OK"
            assert result["model"] == "qwen2.5vl:3b"
            assert "routing_hint" in result
            assert "quality_warnings" in result

    def test_ollama_error(self, fake_allowed_roots, fake_png):
        """Si ollama.chat lève → ok=False mais résultat structuré."""
        target = vision_bridge.VISION_INBOX / "test.png"
        target.write_bytes(fake_png.read_bytes())

        with patch.object(vision_bridge.ollama, "chat", side_effect=RuntimeError("ollama down")):
            result = vision_bridge.analyze_image_file(str(target))
            assert result["ok"] is False
            assert "ollama down" in result["error"]


# ============================================================
# 10. status — dict
# ============================================================

class TestStatus:
    def test_returns_dict(self):
        result = vision_bridge.status()
        assert isinstance(result, dict)

    def test_required_keys(self):
        result = vision_bridge.status()
        for key in ["version", "model", "cpu_ram_only", "paths", "capabilities"]:
            assert key in result

    def test_cpu_ram_only(self):
        result = vision_bridge.status()
        assert result["cpu_ram_only"] is True

    def test_capabilities_complete(self):
        result = vision_bridge.status()
        caps = result["capabilities"]
        assert caps["image_upload"] is True
        assert caps["screenshot_debug"] is True
        assert caps["windows_powershell_bias"] is True
