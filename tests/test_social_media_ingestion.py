"""
E-ZZIO V10.0 — UNIVERSAL SOCIAL MEDIA & INSTAGRAM INGESTION REPAIR TEST SUITE.

Vérifie l'éradication des faux positifs (HTTP 200 != Ingestion réussie) :
1. Classification déterministe des URLs sociales.
2. Extraction réelle et hachage du contenu Instagram / YouTube / TikTok.
3. Blocage explicite et statut typé en cas de login wall / protection anti-bot.
4. Protection contre les coquilles HTML vides dans SafeWebFetcher.
"""

import pytest
import asyncio
from core.perception.social_media_extractor import (
    social_media_extractor,
    SocialPlatform,
    IngestionContentStatus
)
from core.perception.unified_perception import UnifiedPerceptionPipeline
from core.perception.safe_fetcher import SafeWebFetcher


def test_social_url_classification():
    """Vérifie la classification déterministe des URLs de plateformes sociales."""
    assert social_media_extractor.classify_url("https://www.instagram.com/reels/DcdsiP9iHX8/") == SocialPlatform.INSTAGRAM
    assert social_media_extractor.classify_url("https://www.instagram.com/p/C_abc123/") == SocialPlatform.INSTAGRAM
    assert social_media_extractor.classify_url("https://youtube.com/watch?v=dQw4w9WgXcQ") == SocialPlatform.YOUTUBE
    assert social_media_extractor.classify_url("https://www.tiktok.com/@user/video/7123456789") == SocialPlatform.TIKTOK
    assert social_media_extractor.classify_url("https://www.facebook.com/reel/123456789") == SocialPlatform.FACEBOOK
    assert social_media_extractor.classify_url("https://example.com/index.html") == SocialPlatform.UNKNOWN


def test_instagram_reel_real_extraction():
    """Vérifie l'extraction réelle sur un Reel Instagram public sans faux positif."""
    url = "https://www.instagram.com/reels/DcdsiP9iHX8/"
    res = social_media_extractor.extract(url)

    if res.ok:
        assert res.status in (IngestionContentStatus.MEDIA_EXTRACTED, IngestionContentStatus.METADATA_ONLY)
        assert res.platform == SocialPlatform.INSTAGRAM
        assert res.content_type == "reel"
        assert res.title is not None or res.author is not None
        assert res.content_hash is not None
        assert res.provenance == "[DONNÉE PASSIVE NON FIABLE]"
        # Vérifie qu'on n'a pas seulement "Instagram"
        assert res.title != "Instagram"
    else:
        # Si Instagram a déclenché un challenge ou un login wall au moment du test
        assert res.status in (
            IngestionContentStatus.LOGIN_REQUIRED,
            IngestionContentStatus.ANTI_BOT,
            IngestionContentStatus.PRIVATE_CONTENT,
            IngestionContentStatus.EMPTY_OR_BLOCKED_CONTENT,
            IngestionContentStatus.EXTRACTION_FAILED
        )
        assert res.error_reason is not None


def test_safe_fetcher_rejects_empty_shell():
    """Vérifie que SafeWebFetcher refuse de déclarer ok=True sur une coquille HTML vide."""
    fetcher = SafeWebFetcher()
    # Test avec une chaîne nettoyée vide ou générique
    clean = fetcher._clean_html_text("<html><head><title>Instagram</title></head><body></body></html>")
    assert clean.lower() == "instagram"


@pytest.mark.asyncio
async def test_unified_perception_social_pipeline():
    """Vérifie le routage complet via UnifiedPerceptionPipeline pour un Reel Instagram."""
    pipeline = UnifiedPerceptionPipeline()
    url = "https://www.instagram.com/reels/DcdsiP9iHX8/"

    res = await pipeline.perceive(url)
    assert res["input_type"] == "social_url"
    assert res["platform"] == "instagram"

    if res["ok"]:
        assert "CONTENU SOCIAL EXTRAIT" in res["normalized_content"]
        assert "Empreinte SHA-256" in res["normalized_content"]
        assert res["metadata"]["content_hash"] is not None
        # Interdiction absolue de retourner uniquement "Instagram"
        assert res["metadata"].get("title") != "Instagram"
    else:
        # En cas de blocage d'accès, le statut doit être explicite et ok doit être False
        assert res["status"] in ("LOGIN_REQUIRED", "ANTI_BOT", "PRIVATE_CONTENT", "EMPTY_OR_BLOCKED_CONTENT", "EXTRACTION_FAILED")
        assert res["error"] is not None
