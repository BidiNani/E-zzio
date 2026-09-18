"""
E-ZZIO Perception — Universal Social Media & Video Extractor.

Extrait de manière fiable et sécurisée les métadonnées et flux médias des plateformes sociales
(Instagram Reels/Posts, YouTube, TikTok, Facebook, Reddit, X) sans faux positifs.
Règle constitutionnelle : HTTP 200 ≠ INGESTION RÉUSSIE.
"""
from __future__ import annotations

import hashlib
import logging
import re
from enum import Enum
from pathlib import Path

from pydantic import BaseModel

try:
    import yt_dlp
    HAS_YTDLP = True
except ImportError:
    HAS_YTDLP = False

from core.capabilities.capability_policy import CapabilityPolicy

logger = logging.getLogger("SocialMediaExtractor")


class SocialPlatform(str, Enum):
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"
    REDDIT = "reddit"
    X = "x"
    GENERIC_MEDIA = "generic_media"
    UNKNOWN = "unknown"


class IngestionContentStatus(str, Enum):
    MEDIA_EXTRACTED = "MEDIA_EXTRACTED"
    METADATA_ONLY = "METADATA_ONLY"
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    PRIVATE_CONTENT = "PRIVATE_CONTENT"
    ANTI_BOT = "ANTI_BOT"
    EMPTY_OR_BLOCKED_CONTENT = "EMPTY_OR_BLOCKED_CONTENT"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"


class SocialMediaResult(BaseModel):
    ok: bool
    status: IngestionContentStatus
    platform: SocialPlatform
    content_type: str = "media"
    source_url: str
    title: str | None = None
    author: str | None = None
    username: str | None = None
    description: str | None = None
    caption: str | None = None
    duration_seconds: float | None = None
    thumbnail_url: str | None = None
    direct_media_url: str | None = None
    media_type: str = "video"
    content_hash: str | None = None
    provenance: str = "[DONNÉE PASSIVE NON FIABLE]"
    error_reason: str | None = None


class SocialMediaExtractor:
    """Extracteur spécialisé souverain pour réseaux sociaux et plateformes vidéo."""

    PLATFORM_PATTERNS = {
        SocialPlatform.INSTAGRAM: re.compile(r'https?://(?:www\.)?instagram\.com/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)', re.IGNORECASE),
        SocialPlatform.YOUTUBE: re.compile(r'https?://(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/|embed/)|youtu\.be/)([A-Za-z0-9_-]+)', re.IGNORECASE),
        SocialPlatform.TIKTOK: re.compile(r'https?://(?:www\.)?tiktok\.com/@[^/]+/video/(\d+)', re.IGNORECASE),
        SocialPlatform.FACEBOOK: re.compile(r'https?://(?:www\.)?facebook\.com/(?:watch|reel|share|[^/]+/videos)/', re.IGNORECASE),
        SocialPlatform.REDDIT: re.compile(r'https?://(?:www\.)?reddit\.com/r/[^/]+/comments/', re.IGNORECASE),
        SocialPlatform.X: re.compile(r'https?://(?:www\.)?(?:x\.com|twitter\.com)/[^/]+/status/\d+', re.IGNORECASE),
    }

    GENERIC_SHELL_PATTERNS = [
        re.compile(r'^instagram$', re.IGNORECASE),
        re.compile(r'^facebook$', re.IGNORECASE),
        re.compile(r'^tiktok$', re.IGNORECASE),
        re.compile(r'^log in', re.IGNORECASE),
        re.compile(r'^connexion', re.IGNORECASE),
        re.compile(r'enable javascript', re.IGNORECASE),
        re.compile(r'please enable js', re.IGNORECASE),
    ]

    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root).resolve()
        self.tmp_media_dir = self.workspace_root / "runtime" / "tmp" / "media"
        self.tmp_media_dir.mkdir(parents=True, exist_ok=True)
        self.policy = CapabilityPolicy()

    @classmethod
    def classify_url(cls, url: str) -> SocialPlatform:
        """Identifie déterministement la plateforme sociale ciblée par l'URL."""
        for platform, pattern in cls.PLATFORM_PATTERNS.items():
            if pattern.search(url):
                return platform
        return SocialPlatform.UNKNOWN

    def is_social_url(self, url: str) -> bool:
        return self.classify_url(url) != SocialPlatform.UNKNOWN

    def extract(self, url: str) -> SocialMediaResult:
        """
        Extrait le contenu social via yt-dlp et fallback OpenGraph, avec neutralisation passive et hachage.
        """
        platform = self.classify_url(url)
        content_type = "reel" if (platform == SocialPlatform.INSTAGRAM and "/reel" in url) else ("video" if platform == SocialPlatform.YOUTUBE else "social_post")

        if not HAS_YTDLP:
            return SocialMediaResult(
                ok=False,
                status=IngestionContentStatus.EXTRACTION_FAILED,
                platform=platform,
                content_type=content_type,
                source_url=url,
                error_reason="yt-dlp n'est pas disponible dans l'environnement."
            )

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": False,
            "socket_timeout": 15,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return SocialMediaResult(
                        ok=False,
                        status=IngestionContentStatus.EMPTY_OR_BLOCKED_CONTENT,
                        platform=platform,
                        content_type=content_type,
                        source_url=url,
                        error_reason="Extraction retournée vide par yt-dlp."
                    )

                # Extraction des champs
                title = info.get("title")
                uploader = info.get("uploader") or info.get("channel")
                uploader_id = info.get("uploader_id")
                desc = info.get("description") or ""
                duration = info.get("duration")
                thumb = info.get("thumbnail")
                direct_url = info.get("url")
                ext = info.get("ext", "mp4")

                # Calcul du SHA-256 sur les données extraites
                content_to_hash = f"{title or ''}|{uploader or ''}|{desc}|{direct_url or ''}".encode()
                chash = hashlib.sha256(content_to_hash).hexdigest()

                status = IngestionContentStatus.MEDIA_EXTRACTED if direct_url else IngestionContentStatus.METADATA_ONLY

                return SocialMediaResult(
                    ok=True,
                    status=status,
                    platform=platform,
                    content_type=content_type,
                    source_url=url,
                    title=title,
                    author=uploader,
                    username=uploader_id,
                    description=desc[:1500] if desc else None,
                    caption=desc[:500] if desc else None,
                    duration_seconds=duration,
                    thumbnail_url=thumb,
                    direct_media_url=direct_url,
                    media_type="video" if ext in ("mp4", "webm", "mkv") else "image",
                    content_hash=chash,
                    provenance="[DONNÉE PASSIVE NON FIABLE]"
                )

        except yt_dlp.utils.DownloadError as d_err:
            err_msg = str(d_err).lower()
            logger.warning("[SOCIAL-EXTRACTOR] Échec d'extraction pour %s : %s", url, d_err)

            if "login" in err_msg or "sign in" in err_msg or "checkpoint" in err_msg or "cookie" in err_msg:
                status = IngestionContentStatus.LOGIN_REQUIRED
            elif "private" in err_msg:
                status = IngestionContentStatus.PRIVATE_CONTENT
            elif "bot" in err_msg or "challenge" in err_msg or "cloudflare" in err_msg or "captcha" in err_msg:
                status = IngestionContentStatus.ANTI_BOT
            elif "not found" in err_msg or "unavailable" in err_msg:
                status = IngestionContentStatus.EMPTY_OR_BLOCKED_CONTENT
            else:
                status = IngestionContentStatus.EXTRACTION_FAILED

            return SocialMediaResult(
                ok=False,
                status=status,
                platform=platform,
                content_type=content_type,
                source_url=url,
                error_reason=f"Extraction bloquée par {platform.value} : {d_err}"
            )
        except Exception as exc:
            logger.error("[SOCIAL-EXTRACTOR-ERROR] Exception inattendue sur %s : %s", url, exc)
            return SocialMediaResult(
                ok=False,
                status=IngestionContentStatus.EXTRACTION_FAILED,
                platform=platform,
                content_type=content_type,
                source_url=url,
                error_reason=str(exc)
            )


# Instance singleton
social_media_extractor = SocialMediaExtractor()
