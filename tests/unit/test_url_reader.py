"""Tests pour core/url_reader.py.

UrlReader : extraction d'URLs (pur) + fetch HTTP via httpx (async, mocké).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.url_reader import UrlReader

# ============================================================
# 1. extract_urls — pur
# ============================================================

class TestExtractUrls:
    def test_simple_https(self):
        urls = UrlReader.extract_urls("Voir https://example.com pour plus")
        assert urls == ["https://example.com"]

    def test_multiple_urls(self):
        text = "Lien 1 : https://a.com et lien 2 : http://b.org"
        urls = UrlReader.extract_urls(text)
        assert "https://a.com" in urls
        assert "http://b.org" in urls

    def test_www_url(self):
        urls = UrlReader.extract_urls("Visite www.example.com")
        assert "www.example.com" in urls

    def test_no_urls(self):
        assert UrlReader.extract_urls("Aucun lien ici.") == []

    def test_empty_string(self):
        assert UrlReader.extract_urls("") == []

    def test_url_with_path_and_query(self):
        text = "https://api.example.com/v1/users?id=42&format=json"
        urls = UrlReader.extract_urls(text)
        assert "https://api.example.com/v1/users?id=42&format=json" in urls

    def test_url_stops_at_space(self):
        text = "Lien https://example.com/path suite"
        urls = UrlReader.extract_urls(text)
        # Le regex capture jusqu'au \s
        assert "https://example.com/path" in urls

    def test_url_in_parentheses(self):
        text = "(https://example.com)"
        urls = UrlReader.extract_urls(text)
        # Le regex capture jusqu'à >, ", \s — mais pas )
        # Donc "https://example.com)" pourrait être capturé
        assert any("https://example.com" in u for u in urls)


# ============================================================
# 2. fetch_url_content — mock httpx
# ============================================================

class TestFetchUrlContent:
    @pytest.mark.asyncio
    async def test_success_jina(self):
        """Jina Reader répond 200 -> contenu retourné."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "# Page Markdown\n\nContenu de test bien assez long pour passer le check de longueur minimale."

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("core.url_reader.httpx.AsyncClient", return_value=mock_client):
            result = await UrlReader.fetch_url_content("https://example.com")
            assert result is not None
            assert "Contenu de test" in result

    @pytest.mark.asyncio
    async def test_short_jina_response_falls_back(self):
        """Jina répond mais contenu < 50 chars -> fallback direct."""
        short_response = MagicMock()
        short_response.status_code = 200
        short_response.text = "Too short"

        long_response = MagicMock()
        long_response.status_code = 200
        long_response.text = "Direct fetch content with enough length to be considered valid."

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[short_response, long_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("core.url_reader.httpx.AsyncClient", return_value=mock_client):
            result = await UrlReader.fetch_url_content("https://example.com")
            assert "Direct fetch content" in result

    @pytest.mark.asyncio
    async def test_jina_error_falls_back(self):
        """Jina lance une exception -> fallback direct."""
        long_response = MagicMock()
        long_response.status_code = 200
        long_response.text = "Fallback content with enough length."

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[Exception("Jina down"), long_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("core.url_reader.httpx.AsyncClient", return_value=mock_client):
            result = await UrlReader.fetch_url_content("https://example.com")
            assert "Fallback content" in result

    @pytest.mark.asyncio
    async def test_all_fail_returns_none(self):
        """Tous les fetch échouent -> None."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Network down"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("core.url_reader.httpx.AsyncClient", return_value=mock_client):
            result = await UrlReader.fetch_url_content("https://example.com")
            assert result is None

    @pytest.mark.asyncio
    async def test_url_without_scheme_gets_https(self):
        """URL 'www.foo.com' -> préfixée 'https://'."""
        long_response = MagicMock()
        long_response.status_code = 200
        long_response.text = "x" * 100

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=long_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("core.url_reader.httpx.AsyncClient", return_value=mock_client):
            await UrlReader.fetch_url_content("www.foo.com")
            # Vérifier que target_url commence par https://
            calls = mock_client.get.call_args_list
            # Le 1er appel est Jina, l'URL devrait contenir https://www.foo.com
            first_url = calls[0][0][0]
            assert "https://www.foo.com" in first_url

    @pytest.mark.asyncio
    async def test_url_with_scheme_unchanged(self):
        """URL 'https://foo.com' -> inchangée."""
        long_response = MagicMock()
        long_response.status_code = 200
        long_response.text = "x" * 100

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=long_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("core.url_reader.httpx.AsyncClient", return_value=mock_client):
            await UrlReader.fetch_url_content("https://foo.com")
            calls = mock_client.get.call_args_list
            first_url = calls[0][0][0]
            assert "https://foo.com" in first_url

    @pytest.mark.asyncio
    async def test_direct_returns_404_returns_none(self):
        """Jina échoue + direct 404 -> None."""
        err_response = MagicMock()
        err_response.status_code = 404
        err_response.text = ""

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[Exception("jina"), err_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("core.url_reader.httpx.AsyncClient", return_value=mock_client):
            result = await UrlReader.fetch_url_content("https://example.com")
            assert result is None
