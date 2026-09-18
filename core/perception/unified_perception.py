"""E-ZZIO Universal Perception — Unified Perception Gateway.

Ingests ANY external input (URL, image, PDF, audio, video, Office doc, archive, raw text),
routes to the appropriate specialized engine, and normalizes it as passive DATA.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from core.perception.audio_engine import AudioTranscriptionEngine
from core.perception.safe_fetcher import SafeWebFetcher
from core.perception.social_media_extractor import social_media_extractor
from core.perception.universal_reader import UniversalFileReader
from core.perception.vision_engine import VisionEngine

logger = logging.getLogger("UnifiedPerception")


class UnifiedPerceptionPipeline:
    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root).resolve()
        self.reader = UniversalFileReader()
        self.fetcher = SafeWebFetcher()
        self.vision = VisionEngine()
        self.audio = AudioTranscriptionEngine()
        self.social_extractor = social_media_extractor

    async def perceive(
        self,
        input_target: str | Path | bytes,
        user_prompt: str = "",
        mode: str = "auto",
        session_id: str = "default",
        is_last: bool = True
    ) -> dict[str, Any]:
        """Point d'entrée universel : perçoit, décode et normalise n'importe quelle entrée."""
        # 0. Cas flux binaire brut direct (Streaming Audio / Données)
        if isinstance(input_target, bytes):
            audio_res = self.audio.transcribe(input_target, mode="streaming", session_id=session_id, is_last=is_last)
            chunk_txt = audio_res.get("chunk_text", "")
            return {
                "ok": True,
                "input_type": "audio_stream",
                "source": f"stream_session_{session_id}",
                "normalized_content": f"[STREAMING AUDIO CHUNK : {chunk_txt}]",
                "metadata": audio_res
            }

        target_str = str(input_target).strip()

        # 1. Détection de lien web (URL)
        if target_str.startswith("http://") or target_str.startswith("https://"):
            logger.info("[PERCEPTION] Analyse et classification de l'URL : %s", target_str)

            # 1.A. Routage spécialisé Réseaux Sociaux & Vidéo (Instagram, YouTube, TikTok, etc.)
            if self.social_extractor.is_social_url(target_str):
                logger.info("[PERCEPTION] Routage vers l'extracteur média social dédié")
                social_res = self.social_extractor.extract(target_str)
                if not social_res.ok:
                    return {
                        "ok": False,
                        "status": social_res.status.value,
                        "input_type": "social_url",
                        "platform": social_res.platform.value,
                        "source": target_str,
                        "error": social_res.error_reason,
                        "metadata": social_res.model_dump()
                    }

                norm_lines = [
                    f"[CONTENU SOCIAL EXTRAIT ({social_res.platform.value.upper()}) : {target_str}]",
                    f"Statut : {social_res.status.value}",
                    f"Titre : {social_res.title or 'N/A'}",
                    f"Auteur / Chaîne : {social_res.author or 'Inconnu'}",
                    f"Légende / Description : {social_res.caption or social_res.description or 'Aucune'}",
                    f"Flux Média : {social_res.direct_media_url or 'Non téléchargeable directement'}",
                    f"Empreinte SHA-256 : {social_res.content_hash or 'N/A'}",
                    f"Provenance : {social_res.provenance}"
                ]
                return {
                    "ok": True,
                    "status": social_res.status.value,
                    "input_type": "social_url",
                    "platform": social_res.platform.value,
                    "source": target_str,
                    "normalized_content": "\n".join(norm_lines),
                    "metadata": social_res.model_dump()
                }

            # 1.B. Routage Web Générique sécurisé (SafeWebFetcher)
            fetch_res = await self.fetcher.fetch_url(target_str)
            if not fetch_res.get("ok"):
                return fetch_res
            return {
                "ok": True,
                "input_type": "web_url",
                "source": target_str,
                "normalized_content": f"[DONNÉE WEB RÉCUPÉRÉE : {target_str}]\n\n{fetch_res.get('content', '')}",
                "metadata": fetch_res
            }

        # 2. Détection de fichier local
        path = Path(target_str)
        if path.exists() and path.is_file():
            logger.info("[PERCEPTION] Analyse du fichier local : %s", path.name)
            file_res = self.reader.read_file(path)
            if not file_res.get("ok"):
                return file_res

            f_type = file_res.get("type", "")

            # Cas Image / Scan
            if f_type.startswith("image") or file_res.get("status") == "REQUIRES_VISION_OCR":
                vis_res = await self.vision.describe_image(path, prompt=user_prompt)
                analysis_text = vis_res.get("analysis") if vis_res.get("ok") else vis_res.get("error", "Vision indisponible")
                return {
                    "ok": True,
                    "input_type": "image",
                    "source": str(path),
                    "normalized_content": f"[ANALYSE VISUELLE DE L'IMAGE : {path.name}]\n\n{analysis_text}",
                    "metadata": vis_res
                }

            # Cas Audio / Vidéo
            elif f_type.startswith("audio") or f_type == "video" or file_res.get("status") == "REQUIRES_AUDIO_TRANSCRIPTION":
                audio_res = self.audio.transcribe(path)
                transcript_text = audio_res.get("transcript") if audio_res.get("ok") else audio_res.get("error", "Audio indisponible")
                return {
                    "ok": True,
                    "input_type": "audio",
                    "source": str(path),
                    "normalized_content": f"[TRANSCRIPTION AUDIO : {path.name} | Langue : {audio_res.get('detected_language', 'inconnue')}]\n\n{transcript_text}",
                    "metadata": audio_res
                }

            # Cas Document / Texte / PDF / Archive
            else:
                return {
                    "ok": True,
                    "input_type": f_type,
                    "source": str(path),
                    "normalized_content": f"[CONTENU DU DOCUMENT : {path.name}]\n\n{file_res.get('content', '')}",
                    "metadata": file_res
                }

        # 3. Fallback : Texte brut fourni directement
        return {
            "ok": True,
            "input_type": "raw_text",
            "source": "direct_input",
            "normalized_content": target_str,
            "metadata": {"chars_count": len(target_str)}
        }
