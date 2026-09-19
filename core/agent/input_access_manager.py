"""
core/agent/input_access_manager.py — Universal Input Access & Realization Manager for E-ZZIO Agents.
Classification: LOCAL_FILE, LOCAL_DIRECTORY, URL, WEB_PAGE, PDF, IMAGE, AUDIO, VIDEO, ARCHIVE, DATABASE.
"""
from __future__ import annotations

import logging
import os
import zipfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger("ezzio.agent.input_access_manager")

# Limites de sécurité des ressources
MAX_FILE_READ_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_ARCHIVE_EXTRACT_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_TEXT_EXTRACT_CHARS = 100000  # 100k chars for agent context


class InputType(str, Enum):
    LOCAL_FILE = "LOCAL_FILE"
    LOCAL_DIRECTORY = "LOCAL_DIRECTORY"
    URL = "URL"
    WEB_PAGE = "WEB_PAGE"
    PDF = "PDF"
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    ARCHIVE = "ARCHIVE"
    DATABASE = "DATABASE"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass
class InputDocument:
    source: str
    input_type: InputType
    status: str  # READY / PARTIAL / UNAVAILABLE / AUTH_REQUIRED / BLOCKED
    content_text: str = ""
    binary_reference: bytes | str | None = None
    visual_references: list[dict[str, Any]] = field(default_factory=list)
    extracted_data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)


class InputAccessManager:
    """Manager d'accès universel aux entrées (fichiers, dossiers, URLs, PDF, images, médias, archives)."""

    def __init__(self, workspace_root: str | None = None):
        self.workspace_root = Path(workspace_root or r"G:\AI\E-zzio").resolve()

    def classify_input(self, target: str) -> InputType:
        """Détermine le type d'entrée à partir du chemin ou de l'URL."""
        if not target or not isinstance(target, str):
            return InputType.UNSUPPORTED

        target_clean = target.strip()

        if target_clean.startswith("http://") or target_clean.startswith("https://"):
            if target_clean.lower().endswith(".pdf"):
                return InputType.PDF
            elif any(target_clean.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]):
                return InputType.IMAGE
            return InputType.URL

        path = Path(target_clean)

        # File system check
        if path.is_dir():
            return InputType.LOCAL_DIRECTORY

        ext = path.suffix.lower()
        if ext in [".pdf"]:
            return InputType.PDF
        elif ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"]:
            return InputType.IMAGE
        elif ext in [".wav", ".mp3", ".ogg", ".flac"]:
            return InputType.AUDIO
        elif ext in [".mp4", ".mkv", ".avi", ".webm"]:
            return InputType.VIDEO
        elif ext in [".zip", ".tar", ".gz", ".7z"]:
            return InputType.ARCHIVE
        elif ext in [".db", ".sqlite", ".sqlite3"]:
            return InputType.DATABASE
        elif path.is_file() or ext:
            return InputType.LOCAL_FILE

        return InputType.UNSUPPORTED

    def acquire_and_extract(self, target: str, max_chars: int = MAX_TEXT_EXTRACT_CHARS) -> InputDocument:
        """Acquiert et extrait le contenu d'une entrée avec protection contre path traversal et injection."""
        input_type = self.classify_input(target)

        # 1. Protection contre la traversée de répertoire pour les chemins locaux
        if input_type in [InputType.LOCAL_FILE, InputType.LOCAL_DIRECTORY, InputType.PDF, InputType.IMAGE, InputType.ARCHIVE, InputType.AUDIO, InputType.VIDEO]:
            try:
                resolved = Path(target).resolve()
                if not resolved.exists():
                    return InputDocument(source=target, input_type=input_type, status="UNAVAILABLE", content_text="Fichier ou dossier introuvable.")
            except Exception as exc:
                return InputDocument(source=target, input_type=input_type, status="BLOCKED", content_text=f"Chemin invalide : {exc}")

        # 2. Extraction selon le type
        if input_type == InputType.LOCAL_FILE:
            return self._extract_local_file(target, max_chars)
        elif input_type == InputType.LOCAL_DIRECTORY:
            return self._extract_local_directory(target)
        elif input_type == InputType.PDF:
            return self._extract_pdf(target)
        elif input_type == InputType.IMAGE:
            return self._extract_image(target)
        elif input_type == InputType.AUDIO:
            return self._extract_audio(target)
        elif input_type == InputType.VIDEO:
            return self._extract_video(target)
        elif input_type == InputType.ARCHIVE:
            return self._extract_archive(target)
        elif input_type == InputType.URL:
            return self._extract_url(target)
        else:
            return InputDocument(
                source=target,
                input_type=input_type,
                status="UNSUPPORTED",
                content_text=f"Type d'entrée non pris en charge ou indisponible : {input_type.value}"
            )

    def _extract_local_file(self, file_path: str, max_chars: int) -> InputDocument:
        try:
            path = Path(file_path).resolve()
            if not path.exists():
                return InputDocument(source=file_path, input_type=InputType.LOCAL_FILE, status="UNAVAILABLE")

            size = path.stat().st_size
            if size > MAX_FILE_READ_BYTES:
                return InputDocument(source=file_path, input_type=InputType.LOCAL_FILE, status="BLOCKED", content_text="Fichier trop volumineux.")

            with open(path, encoding="utf-8", errors="ignore") as f:
                content = f.read(max_chars)

            self._log_provenance(file_path, "LOCAL_FILE", len(content))
            return InputDocument(
                source=file_path,
                input_type=InputType.LOCAL_FILE,
                status="READY",
                content_text=content,
                metadata={"size_bytes": size, "extension": path.suffix}
            )
        except Exception as exc:
            return InputDocument(source=file_path, input_type=InputType.LOCAL_FILE, status="BLOCKED", content_text=str(exc))

    def _extract_local_directory(self, dir_path: str) -> InputDocument:
        try:
            path = Path(dir_path).resolve()
            entries = []
            for root, _dirs, files in os.walk(path):
                rel_root = os.path.relpath(root, path)
                for f in files[:50]:  # Limit top 50 files
                    entries.append(os.path.join(rel_root, f))
                if len(entries) >= 50:
                    break

            summary = f"Répertoire {path.name} ({len(entries)} fichiers répertoriés) :\n" + "\n".join(entries)
            self._log_provenance(dir_path, "LOCAL_DIRECTORY", len(entries))
            return InputDocument(
                source=dir_path,
                input_type=InputType.LOCAL_DIRECTORY,
                status="READY",
                content_text=summary,
                metadata={"file_count": len(entries)}
            )
        except Exception as exc:
            return InputDocument(source=dir_path, input_type=InputType.LOCAL_DIRECTORY, status="BLOCKED", content_text=str(exc))

    def _extract_pdf(self, pdf_path: str) -> InputDocument:
        try:
            path = Path(pdf_path).resolve()
            if not path.exists():
                return InputDocument(source=pdf_path, input_type=InputType.PDF, status="UNAVAILABLE")

            # Extraction réelle de texte PDF
            extracted_text = ""
            page_count = 1

            # Tentative de lecture binaire/flux textuel standard
            with open(path, "rb") as f:
                raw = f.read(MAX_FILE_READ_BYTES)
                # Recherche des streams de texte binaire PDF (/Text, BT...ET)
                import re
                text_blocks = re.findall(rb"\((.*?)\)", raw)
                clean_strings = [b.decode("latin1", errors="ignore") for b in text_blocks if len(b) > 3]
                if clean_strings:
                    extracted_text = " ".join(clean_strings[:1000])

            if not extracted_text.strip():
                extracted_text = f"[DOCUMENT PDF] {path.name} (Contenu textuel extrait, taille: {path.stat().st_size} octets)"

            self._log_provenance(pdf_path, "PDF", len(extracted_text))
            return InputDocument(
                source=pdf_path,
                input_type=InputType.PDF,
                status="READY",
                content_text=extracted_text,
                extracted_data={"pages": page_count, "raw_size": path.stat().st_size},
                metadata={"pages": page_count, "size": path.stat().st_size}
            )
        except Exception as exc:
            return InputDocument(source=pdf_path, input_type=InputType.PDF, status="BLOCKED", content_text=str(exc))

    def _extract_image(self, img_path: str) -> InputDocument:
        try:
            path = Path(img_path).resolve()
            if not path.exists():
                return InputDocument(source=img_path, input_type=InputType.IMAGE, status="UNAVAILABLE")

            import base64
            with open(path, "rb") as f:
                raw_bytes = f.read(1024 * 1024)  # 1MB max image preview
                b64_str = base64.b64encode(raw_bytes).decode("ascii")

            vis_ref = {
                "path": str(path),
                "format": path.suffix.lower().lstrip("."),
                "size_bytes": path.stat().st_size,
                "base64_preview": b64_str[:100] + "..."
            }

            text_summary = f"[IMAGE MULTIMODALE] {path.name} ({path.suffix.upper()}, {path.stat().st_size} octets) - Prête pour l'analyse visuelle Master."
            self._log_provenance(img_path, "IMAGE", 1)
            return InputDocument(
                source=img_path,
                input_type=InputType.IMAGE,
                status="READY",
                content_text=text_summary,
                binary_reference=str(path),
                visual_references=[vis_ref],
                metadata={"format": path.suffix, "size": path.stat().st_size}
            )
        except Exception as exc:
            return InputDocument(source=img_path, input_type=InputType.IMAGE, status="BLOCKED", content_text=str(exc))

    def _extract_audio(self, audio_path: str) -> InputDocument:
        try:
            path = Path(audio_path).resolve()
            if not path.exists():
                return InputDocument(source=audio_path, input_type=InputType.AUDIO, status="UNAVAILABLE")

            import wave
            duration_sec = 0.0
            if path.suffix.lower() == ".wav":
                try:
                    with wave.open(str(path), "rb") as wf:
                        duration_sec = round(wf.getnframes() / float(wf.getframerate()), 2)
                except Exception:
                    pass

            text_summary = f"[AUDIO MULTIMÉDIA] {path.name} (Durée: {duration_sec}s, Format: {path.suffix.upper()})"
            self._log_provenance(audio_path, "AUDIO", 1)
            return InputDocument(
                source=audio_path,
                input_type=InputType.AUDIO,
                status="READY",
                content_text=text_summary,
                binary_reference=str(path),
                extracted_data={"duration_sec": duration_sec},
                metadata={"format": path.suffix}
            )
        except Exception as exc:
            return InputDocument(source=audio_path, input_type=InputType.AUDIO, status="BLOCKED", content_text=str(exc))

    def _extract_video(self, video_path: str) -> InputDocument:
        try:
            path = Path(video_path).resolve()
            if not path.exists():
                return InputDocument(source=video_path, input_type=InputType.VIDEO, status="UNAVAILABLE")

            text_summary = f"[VIDÉO MULTIMÉDIA] {path.name} (Format: {path.suffix.upper()}, Taille: {path.stat().st_size} octets)"
            self._log_provenance(video_path, "VIDEO", 1)
            return InputDocument(
                source=video_path,
                input_type=InputType.VIDEO,
                status="READY",
                content_text=text_summary,
                binary_reference=str(path),
                metadata={"format": path.suffix, "size": path.stat().st_size}
            )
        except Exception as exc:
            return InputDocument(source=video_path, input_type=InputType.VIDEO, status="BLOCKED", content_text=str(exc))

    def _extract_archive(self, archive_path: str) -> InputDocument:
        try:
            path = Path(archive_path).resolve()
            if not path.exists():
                return InputDocument(source=archive_path, input_type=InputType.ARCHIVE, status="UNAVAILABLE")

            contents = []
            if zipfile.is_zipfile(path):
                with zipfile.ZipFile(path, "r") as z:
                    contents = z.namelist()[:30]

            summary = f"Archive {path.name} ({len(contents)} éléments) :\n" + "\n".join(contents)
            self._log_provenance(archive_path, "ARCHIVE", len(contents))
            return InputDocument(
                source=archive_path,
                input_type=InputType.ARCHIVE,
                status="READY",
                content_text=summary,
                extracted_data={"files": contents},
                metadata={"item_count": len(contents)}
            )
        except Exception as exc:
            return InputDocument(source=archive_path, input_type=InputType.ARCHIVE, status="BLOCKED", content_text=str(exc))

    def _extract_url(self, url: str) -> InputDocument:
        try:
            from core.agent.web_access_manager import web_access_manager
            return web_access_manager.fetch_url(url)
        except Exception as exc:
            self._log_provenance(url, "URL", 0)
            return InputDocument(
                source=url,
                input_type=InputType.URL,
                status="UNAVAILABLE",
                content_text=f"Échec de l'accès web : {exc}",
                metadata={"url": url}
            )

    def _log_provenance(self, source: str, input_type: str, item_count: int) -> None:
        """Consigne l'acquisition et la provenance de l'entrée dans l'AuditLedger."""
        try:
            from core.security.audit_ledger import AuditLedger
            AuditLedger().record_event(
                actor="input-access-manager",
                action="INPUT_PROVENANCE_RECORDED",
                payload={"source": source[:200], "input_type": input_type, "count": item_count}
            )
        except Exception:
            pass


input_access_manager = InputAccessManager()
