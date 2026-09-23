"""Tests pour core/config/active_model.py."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from core.config import active_model as am


@pytest.fixture
def tmp_runtime(tmp_path):
    """Redirige _ACTIVE_MODEL_FILE vers un dossier temporaire."""
    fake_file = tmp_path / "active_model.json"
    with patch.object(am, "_ACTIVE_MODEL_FILE", fake_file):
        with patch.object(am, "_RUNTIME_DIR", tmp_path):
            yield fake_file


class TestGetActiveModel:
    def test_returns_default_if_file_missing(self, tmp_runtime):
        result = am.get_active_model()
        assert result["provider"] == am.DEFAULT_MODEL["provider"]
        assert result["model_id"] == am.DEFAULT_MODEL["model_id"]

    def test_reads_file_if_exists(self, tmp_runtime):
        tmp_runtime.write_text(
            json.dumps({"provider": "groq", "model_id": "llama-3"}),
            encoding="utf-8",
        )
        result = am.get_active_model()
        assert result["provider"] == "groq"
        assert result["model_id"] == "llama-3"

    def test_corrupted_file_returns_default(self, tmp_runtime):
        tmp_runtime.write_text("{invalid json", encoding="utf-8")
        result = am.get_active_model()
        assert result == dict(am.DEFAULT_MODEL)

    def test_file_without_keys_returns_default(self, tmp_runtime):
        tmp_runtime.write_text(json.dumps({"foo": "bar"}), encoding="utf-8")
        result = am.get_active_model()
        assert result == dict(am.DEFAULT_MODEL)


class TestSetActiveModel:
    def test_writes_file(self, tmp_runtime):
        result = am.set_active_model("groq", "llama-3", "LLaMA 3")
        assert result["provider"] == "groq"
        assert result["model_id"] == "llama-3"
        assert result["display_name"] == "LLaMA 3"
        assert tmp_runtime.exists()

    def test_display_name_defaults_to_model_id(self, tmp_runtime):
        result = am.set_active_model("groq", "llama-3")
        assert result["display_name"] == "llama-3"


class TestGetActiveGeminiModel:
    def test_returns_active_if_gemini(self, tmp_runtime):
        tmp_runtime.write_text(
            json.dumps({"provider": "gemini", "model_id": "gemini-4.0"}),
            encoding="utf-8",
        )
        assert am.get_active_gemini_model() == "gemini-4.0"

    def test_returns_default_if_other_provider(self, tmp_runtime):
        tmp_runtime.write_text(
            json.dumps({"provider": "groq", "model_id": "llama-3"}),
            encoding="utf-8",
        )
        assert am.get_active_gemini_model() == am.DEFAULT_MODEL["model_id"]

    def test_returns_default_if_no_file(self, tmp_runtime):
        assert am.get_active_gemini_model() == am.DEFAULT_MODEL["model_id"]

