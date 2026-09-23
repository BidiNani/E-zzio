"""Tests pour core/providers/tavily_provider.py."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.providers.tavily_provider import TavilyProvider


class TestTavilyProviderInit:
    def test_name(self):
        with patch("core.providers.tavily_provider.load_secrets"):
            p = TavilyProvider(api_key="test-key")
            assert p.name == "tavily"

    def test_base_url(self):
        with patch("core.providers.tavily_provider.load_secrets"):
            p = TavilyProvider(api_key="test-key")
            assert p.base_url == "https://api.tavily.com/search"


class TestTavilyProviderSearch:
    @pytest.mark.asyncio
    async def test_raises_without_api_key(self):
        with patch("core.providers.tavily_provider.load_secrets"):
            with patch.dict("os.environ", {}, clear=True):
                p = TavilyProvider(api_key=None)
                with pytest.raises(RuntimeError, match="TAVILY_API_KEY"):
                    await p.search("query")

    @pytest.mark.asyncio
    async def test_successful_search(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "results": [{"title": "r1"}, {"title": "r2"}],
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("core.providers.tavily_provider.load_secrets"):
            with patch("core.providers.tavily_provider.httpx.AsyncClient", return_value=mock_client):
                p = TavilyProvider(api_key="test-key")
                result = await p.search("test query")

        assert result["provider"] == "tavily"
        assert len(result["data"]["results"]) == 2
        assert result["data"]["total"] == 2

    @pytest.mark.asyncio
    async def test_custom_max_results(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"results": []}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("core.providers.tavily_provider.load_secrets"):
            with patch("core.providers.tavily_provider.httpx.AsyncClient", return_value=mock_client):
                p = TavilyProvider(api_key="test-key")
                await p.search("q", max_results=10)

        call_kwargs = mock_client.post.call_args.kwargs
        assert call_kwargs["json"]["max_results"] == 10

