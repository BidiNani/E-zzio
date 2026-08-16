import pytest
from core.providers.ollama_provider import OllamaProvider

@pytest.mark.asyncio
async def test_ollama_provider_structure():
    provider = OllamaProvider()
    assert provider.name == "ollama"
    assert provider.model == "qwen2.5:7b"
