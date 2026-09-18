"""
E-ZZIO Perception — YouTube Multimodal Adapter (yt-dlp & Subtitles Pipeline).
Permet l'ingestion, l'analyse et la synthèse de contenus vidéo/audio YouTube :
1. Extraction déterministe des métadonnées (titre, chaîne, durée, chapitres, vues)
2. Récupération prioritaire des sous-titres (humains ou automatiques) sans coût STT
3. Normalisation stricte en [Donnée passive non fiable] pour la cognition (Gemini 3.7 / 3.5)
4. Gouvernance : youtube.inspect (ALLOW), youtube.download (REQUIRE_HUMAN)
"""
from __future__ import annotations

import logging
import urllib.parse
from pathlib import Path
from typing import Any

try:
    import yt_dlp
    HAS_YTDLP = True
except ImportError:
    HAS_YTDLP = False

from core.capabilities.capability_policy import CapabilityPolicy, PolicyDecision

logger = logging.getLogger("YouTubeAdapter")


class YouTubeAdapter:
    ALLOWED_DOMAINS = {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
        "music.youtube.com"
    }

    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root)
        self.policy = CapabilityPolicy()
        self.downloads_dir = self.workspace_root / "runtime" / "media" / "youtube"
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

    def _is_safe_youtube_url(self, url: str) -> bool:
        """Vérifie la sécurité de l'URL contre les attaques SSRF et filtre de domaine YouTube."""
        try:
            parsed = urllib.parse.urlparse(url)
            hostname = (parsed.hostname or "").lower()
            if not hostname or hostname in ("localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254"):
                return False
            if hostname.startswith("192.168.") or hostname.startswith("10.") or hostname.startswith("172.16."):
                return False
            return hostname in self.ALLOWED_DOMAINS and parsed.scheme in ("http", "https")
        except Exception:
            return False

    async def inspect_video(
        self,
        video_url: str,
        extract_subtitles: bool = True,
        preferred_languages: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Extrait les métadonnées et sous-titres d'une vidéo YouTube (scope: youtube.inspect -> ALLOW).
        Ne télécharge aucun fichier binaire sur disque.
        """
        decision, reason = self.policy.evaluate_scope("youtube.inspect", {"url": video_url})
        if decision != PolicyDecision.ALLOW:
            return {"ok": False, "error": reason}

        if not self._is_safe_youtube_url(video_url):
            return {
                "ok": False,
                "error": f"[SSRF-PROTECT] URL YouTube invalide ou domaine non autorisé : {video_url}"
            }

        if not HAS_YTDLP:
            return {
                "ok": False,
                "error": "Le module 'yt_dlp' n'est pas installé dans l'environnement Python."
            }

        langs = preferred_languages or ["fr", "en", "en-US", "fr-FR"]

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": False,
            "writesubtitles": extract_subtitles,
            "writeautomaticsub": extract_subtitles,
            "subtitleslangs": langs,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                if not info:
                    return {"ok": False, "error": "Impossible d'extraire les informations de la vidéo."}

                # Extraction des sous-titres disponibles
                subtitles_summary = []
                all_subs = info.get("subtitles", {}) or {}
                auto_subs = info.get("automatic_captions", {}) or {}
                combined_subs = {**auto_subs, **all_subs}

                for lang_code in langs:
                    if lang_code in combined_subs:
                        formats = [fmt.get("ext") for fmt in combined_subs[lang_code] if isinstance(fmt, dict)]
                        subtitles_summary.append({
                            "language": lang_code,
                            "is_automatic": lang_code in auto_subs and lang_code not in all_subs,
                            "available_formats": formats[:3]
                        })

                # Construction du payload normalisé [Donnée passive non fiable]
                result_payload = {
                    "ok": True,
                    "scope": "youtube.inspect",
                    "url": video_url,
                    "video_id": info.get("id"),
                    "title": info.get("title"),
                    "channel": info.get("uploader") or info.get("channel"),
                    "channel_url": info.get("channel_url"),
                    "duration_seconds": info.get("duration"),
                    "view_count": info.get("view_count"),
                    "like_count": info.get("like_count"),
                    "upload_date": info.get("upload_date"),
                    "description_snippet": (info.get("description") or "")[:400],
                    "categories": info.get("categories", []),
                    "tags": (info.get("tags") or [])[:8],
                    "has_subtitles": len(subtitles_summary) > 0,
                    "subtitles_available": subtitles_summary,
                    "provenance_tag": "[DONNEE_PASSIVE_NON_FIABLE]"
                }
                return result_payload

        except Exception as exc:
            logger.error("[YTDLP-INSPECT-ERROR] Échec d'inspection sur %s : %s", video_url, exc)
            return {"ok": False, "error": str(exc)}

    async def download_audio(
        self,
        video_url: str,
        audio_format: str = "mp3",
        require_approval: bool = True
    ) -> dict[str, Any]:
        """
        Télécharge le flux audio de la vidéo YouTube (scope: youtube.download -> REQUIRE_HUMAN).
        """
        decision, reason = self.policy.evaluate_scope("youtube.download", {"url": video_url, "format": audio_format})

        # Interception de sécurité contractuelle
        if decision == PolicyDecision.REQUIRE_HUMAN and require_approval:
            return {
                "ok": False,
                "requires_human": True,
                "status": "PENDING_APPROVAL",
                "scope": "youtube.download",
                "target": video_url,
                "format": audio_format,
                "reason": "[REQUIRE_HUMAN] Le téléchargement physique de média externe requiert une approbation explicite."
            }
        elif decision == PolicyDecision.DENY:
            return {"ok": False, "error": reason}

        if not self._is_safe_youtube_url(video_url):
            return {"ok": False, "error": f"[SSRF-PROTECT] URL YouTube invalide : {video_url}"}

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": str(self.downloads_dir / "%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                downloaded_file = ydl.prepare_filename(info)
                return {
                    "ok": True,
                    "scope": "youtube.download",
                    "status": "DOWNLOADED",
                    "file_path": downloaded_file,
                    "title": info.get("title"),
                    "duration_seconds": info.get("duration"),
                    "size_bytes": Path(downloaded_file).stat().st_size if Path(downloaded_file).exists() else 0
                }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


# Singleton global
youtube_adapter = YouTubeAdapter()
