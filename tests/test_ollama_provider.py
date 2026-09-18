import pytest

from core.providers.ollama_provider import OllamaProvider


@pytest.mark.asyncio
async def test_ollama_provider_structure():
    provider = OllamaProvider()
    assert provider.name == "ollama"
    assert "11434" in provider.base_url
    assert "qwen" in provider.model.lower()
