"""Tests critiques pour core/providers/gemini_provider.py."""
import pytest


def test_gemini_default_model_is_3_6():
    from core.providers.gemini_provider import GeminiProvider
    assert GeminiProvider.DEFAULT_MODEL == "gemini-3.6-flash"


def test_gemini_no_2_5_in_default():
    from core.providers.gemini_provider import GeminiProvider
    assert "2.5" not in GeminiProvider.DEFAULT_MODEL
    assert "2.0" not in GeminiProvider.DEFAULT_MODEL


def test_gemini_fallbacks_have_3_6():
    from core.providers.gemini_provider import GeminiProvider
    assert "gemini-3.6-flash" in GeminiProvider.FALLBACK_MODELS


def test_gemini_provider_init_default():
    from core.providers.gemini_provider import GeminiProvider
    p = GeminiProvider(api_key="K0")
    assert p.model == "gemini-3.6-flash"
