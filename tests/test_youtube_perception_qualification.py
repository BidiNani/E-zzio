"""
E-ZZIO Test Suite — YouTube Perception Capability Qualification.
Certifie la qualification de l'adaptateur multimodal YouTube (yt-dlp) :
1. Protection SSRF stricte et filtrage des domaines autorisés
2. Extraction normalisée des métadonnées avec marquage [Donnée passive non fiable]
3. Interception de sécurité REQUIRE_HUMAN sur le téléchargement de média
4. Intégration et gouvernance dans CapabilityRegistry
"""
import pytest

from core.capabilities.registry import CapabilityRegistry, QualificationStatus
from core.perception.youtube_adapter import YouTubeAdapter


def test_youtube_adapter_ssrf_protection():
    adapter = YouTubeAdapter()

    # Domaines autorisés
    assert adapter._is_safe_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert adapter._is_safe_youtube_url("https://youtu.be/dQw4w9WgXcQ") is True
    assert adapter._is_safe_youtube_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ") is True

    # Attaques SSRF et domaines tiers interdits
    assert adapter._is_safe_youtube_url("http://127.0.0.1/watch?v=123") is False
    assert adapter._is_safe_youtube_url("http://169.254.169.254/latest/meta-data") is False
    assert adapter._is_safe_youtube_url("https://evil-site.com/video.mp4") is False
    assert adapter._is_safe_youtube_url("file:///etc/passwd") is False


@pytest.mark.asyncio
async def test_youtube_adapter_inspect_ssrf_rejection():
    adapter = YouTubeAdapter()
    res = await adapter.inspect_video("http://127.0.0.1/malicious_probe")
    assert res["ok"] is False
    assert "[SSRF-PROTECT]" in res["error"]


@pytest.mark.asyncio
async def test_youtube_adapter_require_human_download():
    adapter = YouTubeAdapter()
    # Le téléchargement de média physique requiert une approbation humaine
    res = await adapter.download_audio("https://www.youtube.com/watch?v=dQw4w9WgXcQ", require_approval=True)
    assert res["ok"] is False
    assert res["requires_human"] is True
    assert res["status"] == "PENDING_APPROVAL"
    assert res["scope"] == "youtube.download"
    assert "[REQUIRE_HUMAN]" in res["reason"]


@pytest.mark.asyncio
async def test_youtube_registry_integration():
    reg = CapabilityRegistry()
    qual = reg.get_qualification("youtube-adapter")
    assert qual is not None
    assert qual.status == QualificationStatus.QUALIFIED
    assert qual.category == "multimodal_perception"
    assert "youtube.inspect" in qual.permissions
    assert "youtube.download" in qual.permissions
    assert qual.fail_closed is True
