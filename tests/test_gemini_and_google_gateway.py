import pytest
from core.providers.gemini_provider import GeminiProvider
from core.providers.google_gateway import GoogleToolsGateway
from core.providers.igoogle_provider import IGoogleProvider

class MockGoogleService(IGoogleProvider):
    async def execute(self, **kwargs):
        return {"provider": "mock_google", "status": "success", "action": kwargs.get("action")}

@pytest.mark.asyncio
async def test_gemini_provider_init_and_attributes():
    provider = GeminiProvider(api_key="test_key", model="gemini-1.5-pro")
    assert provider.name == "gemini"
    assert provider.model == "gemini-1.5-pro"
    assert "v1beta" in provider.base_url

@pytest.mark.asyncio
async def test_google_gateway_dispatch():
    gateway = GoogleToolsGateway()
    gateway.register_provider("mock", MockGoogleService())

    res = await gateway.execute("mock", action="list_items")
    assert res["provider"] == "mock_google"
    assert res["status"] == "success"
    assert res["action"] == "list_items"

@pytest.mark.asyncio
async def test_google_gateway_unknown_service():
    gateway = GoogleToolsGateway()
    with pytest.raises(ValueError, match="Service Google inconnu"):
        await gateway.execute("unknown_service")
