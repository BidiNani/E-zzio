"""
Test unitaire du CapabilityRegistry et de la qualification formelle de web-search-mcp et crawl4ai-engine.
"""
import pytest
from unittest.mock import patch, AsyncMock
import httpx
from core.capabilities.registry import CapabilityRegistry, capability_registry
from core.capabilities.capability_qualification import CapabilityQualification, QualificationStatus


def test_capability_registry_initialization():
    qualified = capability_registry.list_qualified_capabilities()
    assert "web-search-mcp" in qualified
    assert "crawl4ai-engine" in qualified
    assert "github-mcp" in qualified

    # Vérification des propriétés de sécurité de web-search-mcp
    q_search = capability_registry.get_qualification("web-search-mcp")
    assert q_search is not None
    assert q_search.ssrf_protection is True
    assert q_search.fail_closed is True
    assert q_search.status == QualificationStatus.QUALIFIED


@pytest.mark.asyncio
async def test_capability_execute_web_search_mcp():
    mock_html = """
    <div class="result__body">
        <a class="result__url" href="https://example.com/test">example.com</a>
        <a class="result__title">Résultat Test</a>
        <a class="result__snippet">Description du résultat</a>
    </div>
    """
    mock_resp = httpx.Response(200, text=mock_html)

    with patch.object(httpx.AsyncClient, "post", return_value=mock_resp):
        res = await capability_registry.execute_capability("web-search-mcp", {"query": "python", "limit": 3})
        assert res["ok"] is True
        assert res["scope"] == "web.search"
        assert res["count"] == 1
        assert res["data"][0]["title"] == "Résultat Test"
        assert res["data"][0]["url"] == "https://example.com/test"


@pytest.mark.asyncio
async def test_capability_execute_crawl4ai_engine():
    mock_html = """
    <html>
        <head><style>body { color: red; }</style></head>
        <body>
            <h1>Titre Principal</h1>
            <p>Paragraphe informatif.</p>
            <script>alert("hack");</script>
        </body>
    </html>
    """
    mock_resp = httpx.Response(200, text=mock_html)

    with patch.object(httpx.AsyncClient, "get", return_value=mock_resp):
        res = await capability_registry.execute_capability("crawl4ai-engine", {"target_url": "https://example.com/doc"})
        assert res["ok"] is True
        assert res["scope"] == "web.crawl"
        assert "# Titre Principal" in res["content"]
        assert "Paragraphe informatif." in res["content"]
        assert "alert(" not in res["content"]  # Scripts épurés


@pytest.mark.asyncio
async def test_capability_fail_closed_on_unregistered_or_quarantined():
    # 1. Capacité inconnue -> rejet immédiat
    res_unknown = await capability_registry.execute_capability("unregistered-tool", {"foo": "bar"})
    assert res_unknown["ok"] is False
    assert "non enregistrée" in res_unknown["error"]

    # 2. Capacité en quarantaine -> exécution interdite
    custom_registry = CapabilityRegistry()
    custom_registry.register(
        CapabilityQualification(
            name="quarantined-tool",
            category="web",
            provider="dummy",
            input_contract={},
            output_contract={},
            status=QualificationStatus.QUARANTINED
        )
    )
    res_quar = await custom_registry.execute_capability("quarantined-tool", {})
    assert res_quar["ok"] is False
    assert "QUARANTINED" in res_quar["error"]
