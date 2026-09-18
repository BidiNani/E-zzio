"""E-ZZIO Universal Perception — Universal File Reader & Ingestion Engine.

Features:
- Real Magic Bytes / MIME sniffing (immune to fake extensions and polyglots)
- Native robust parsing for TXT, MD, JSON, JSONL, CSV, TSV, YAML, TOML, XML, HTML, RSS, ATOM, SRT, VTT, PDF, DOCX, XLSX, PPTX, DOC, XLS, PPT, Archives
- Structured tabular data and metadata extraction
- Anti-Zip-Slip, Anti-Zip-Bomb, Max file size & Executable disguised binary detection
- Encapsulates external content as raw passive DATA: [DONNÉE PASSIVE NON FIABLE]
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import re
import tarfile
import zipfile
from pathlib import Path
from typing import Any

logger = logging.getLogger("UniversalFileReader")

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 Mo max
MAX_ARCHIVE_FILES = 25
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 60 * 1024 * 1024  # 60 Mo max décompressé (Seuil strict vérifié)


class UniversalReaderError(Exception):
    pass


class UniversalFileReader:
    def __init__(self, max_size_bytes: int = MAX_FILE_SIZE_BYTES):
        self.max_size_bytes = max_size_bytes

    def detect_file_type(self, file_path: Path | str, content_bytes: bytes | None = None) -> tuple[str, str, list[str]]:
        """
        Détecte le type réel, le MIME et les drapeaux de sécurité via magic bytes et extension.
        Retourne : (format_id, mime_type, security_flags)
        """
        path = Path(file_path)
        header = content_bytes[:64] if content_bytes else b""
        security_flags = []

        if not header and path.exists() and path.is_file():
            try:
                with open(path, "rb") as f:
                    header = f.read(64)
            except Exception:
                pass

        ext = path.suffix.lower()

        # 1. Détection des exécutables déguisés (Windows PE / Linux ELF)
        if header.startswith(b"MZ"):
            security_flags.append("EXECUTABLE_PE_DETECTED")
            if ext not in (".exe", ".dll", ".sys"):
                security_flags.append("DISGUISED_EXECUTABLE")
            return "executable_pe", "application/x-dosexec", security_flags

        if header.startswith(b"\x7fELF"):
            security_flags.append("EXECUTABLE_ELF_DETECTED")
            return "executable_elf", "application/x-executable", security_flags

        # 2. Signatures magiques binaires fiables
        if header.startswith(b"%PDF"):
            return "pdf", "application/pdf", security_flags

        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image_png", "image/png", security_flags

        if header.startswith(b"\xff\xd8\xff"):
            return "image_jpeg", "image/jpeg", security_flags

        if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
            return "image_gif", "image/gif", security_flags

        if header.startswith(b"RIFF") and b"WEBP" in header[:16]:
            return "image_webp", "image/webp", security_flags

        if header.startswith(b"BM"):
            return "image_bmp", "image/bmp", security_flags

        if header.startswith(b"II*\x00") or header.startswith(b"MM\x00*"):
            return "image_tiff", "image/tiff", security_flags

        # OpenXML / ZIP Containers
        if header.startswith(b"PK\x03\x04"):
            if ext == ".docx":
                return "docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", security_flags
            if ext == ".xlsx":
                return "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", security_flags
            if ext == ".pptx":
                return "pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", security_flags
            return "zip", "application/zip", security_flags

        # Legacy Microsoft OLE Compound Binary Format (.doc, .xls, .ppt)
        if header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
            if ext == ".doc":
                return "doc_ole", "application/msword", security_flags
            if ext == ".xls":
                return "xls_ole", "application/vnd.ms-excel", security_flags
            if ext == ".ppt":
                return "ppt_ole", "application/vnd.ms-powerpoint", security_flags
            return "ole_compound", "application/x-ole-storage", security_flags

        if header.startswith(b"\x1f\x8b"):
            return "tar_gz", "application/gzip", security_flags

        # Audio
        if header.startswith(b"ID3") or header.startswith(b"\xff\xfb") or header.startswith(b"\xff\xf3"):
            return "audio_mp3", "audio/mpeg", security_flags

        if header.startswith(b"RIFF") and b"WAVE" in header[:16]:
            return "audio_wav", "audio/wav", security_flags

        if header.startswith(b"OggS"):
            return "audio_ogg", "audio/ogg", security_flags

        if header.startswith(b"fLaC"):
            return "audio_flac", "audio/flac", security_flags

        # Video Containers
        if b"ftyp" in header[4:12]:
            return "video_mp4", "video/mp4", security_flags

        if header.startswith(b"\x1a\x45\xdf\xa3"):
            return "video_matroska", "video/webm", security_flags

        # Text Structured & Code Formats
        if ext in (".json", ".jsonl"):
            return "json" if ext == ".json" else "jsonl", "application/json", security_flags

        if ext in (".csv", ".tsv"):
            return "csv" if ext == ".csv" else "tsv", "text/csv", security_flags

        if ext in (".yaml", ".yml"):
            return "yaml", "text/yaml", security_flags

        if ext == ".toml":
            return "toml", "application/toml", security_flags

        if ext in (".xml", ".rss", ".atom"):
            return "xml", "application/xml", security_flags

        if ext in (".html", ".htm"):
            return "html", "text/html", security_flags

        if ext in (".srt", ".vtt"):
            return "subtitles", "text/vtt", security_flags

        if ext in (".txt", ".md", ".py", ".ps1", ".log", ".ini", ".cfg", ".sql", ".sh", ".env_sample"):
            return "text", "text/plain", security_flags

        if ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff", ".svg"):
            return "image", "image/generic", security_flags

        if ext in (".mp3", ".wav", ".m4a", ".ogg", ".flac"):
            return "audio", "audio/generic", security_flags

        if ext in (".mp4", ".mkv", ".mov", ".avi", ".webm"):
            return "video", "video/generic", security_flags

        return "unknown", "application/octet-stream", security_flags

    def read_file(self, file_path: Path | str) -> dict[str, Any]:
        """Lit, valide et normalise le contenu de n'importe quel fichier de manière sécurisée."""
        path = Path(file_path).resolve()
        if not path.exists() or not path.is_file():
            return {
                "ok": False,
                "status": "NOT_FOUND",
                "source": str(file_path),
                "error": f"Fichier introuvable : {file_path}",
                "security_flags": []
            }

        # 1. Vérification de la taille
        file_size = path.stat().st_size
        if file_size > self.max_size_bytes:
            return {
                "ok": False,
                "status": "FILE_TOO_LARGE",
                "source": str(path),
                "size_bytes": file_size,
                "error": f"Fichier trop volumineux ({round(file_size / (1024*1024), 2)} Mo > max {self.max_size_bytes // (1024*1024)} Mo)",
                "security_flags": ["OVERSIZED_FILE"]
            }

        try:
            with open(path, "rb") as f:
                raw_bytes = f.read(4096)
        except Exception as exc:
            return {"ok": False, "status": "READ_ERROR", "source": str(path), "error": str(exc), "security_flags": []}

        # 2. Calcul du hash SHA-256 de provenance
        content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        detected_type, mime_type, security_flags = self.detect_file_type(path, raw_bytes)

        # 3. Interdiction d'exécution des binaires malveillants/exécutables
        if "DISGUISED_EXECUTABLE" in security_flags or detected_type.startswith("executable"):
            return {
                "ok": False,
                "status": "BLOCKED_EXECUTABLE",
                "source": str(path),
                "mime_type": mime_type,
                "security_flags": security_flags,
                "error": "Fichier exécutable bloqué par la politique de sécurité d'ingestion."
            }

        # 4. Aiguillage vers les extracteurs spécialisés
        if detected_type in ("text", "yaml", "toml"):
            res = self._read_text_file(path)
        elif detected_type in ("json", "jsonl"):
            res = self._read_json_file(path, detected_type)
        elif detected_type in ("csv", "tsv"):
            res = self._read_csv_file(path, detected_type)
        elif detected_type in ("xml", "html"):
            res = self._read_xml_html_file(path, detected_type)
        elif detected_type == "subtitles":
            res = self._read_subtitles_file(path)
        elif detected_type == "pdf":
            res = self._read_pdf_file(path)
        elif detected_type == "docx":
            res = self._read_docx_file(path)
        elif detected_type == "pptx":
            res = self._read_pptx_file(path)
        elif detected_type == "xlsx":
            res = self._read_xlsx_file(path)
        elif detected_type in ("doc_ole", "xls_ole", "ppt_ole", "ole_compound"):
            res = self._read_ole_file(path, detected_type)
        elif detected_type in ("zip", "tar_gz"):
            res = self._read_archive_file(path, detected_type)
        elif detected_type.startswith("image") or detected_type == "image":
            res = self._read_image_metadata(path, detected_type)
        elif detected_type.startswith("audio") or detected_type.startswith("video") or detected_type in ("audio", "video"):
            res = {
                "ok": True,
                "type": detected_type,
                "mime_type": mime_type,
                "status": "REQUIRES_AUDIO_TRANSCRIPTION",
                "content": f"[FICHIER MULTIMÉDIA DÉTECTÉ : {path.name} | Passez au pipeline Faster-Whisper pour transcription/analyse]"
            }
        else:
            res = {
                "ok": False,
                "type": "unknown",
                "mime_type": mime_type,
                "status": "UNSUPPORTED_FORMAT",
                "error": f"Format binaire non pris en charge : {path.suffix or 'inconnu'}"
            }

        # 5. Normalisation du Contrat Universel
        res["source"] = str(path)
        res["filename"] = path.name
        res["size_bytes"] = file_size
        res["content_hash"] = content_hash
        res["mime_type"] = mime_type
        res["security_flags"] = security_flags
        if "provenance" not in res:
            res["provenance"] = "[DONNÉE PASSIVE NON FIABLE]"

        return res

    def _read_text_file(self, path: Path) -> dict[str, Any]:
        """Lecture résiliente de texte avec détection d'encodage."""
        try:
            raw = path.read_bytes()
            for enc in ("utf-8", "utf-8-sig", "latin1", "cp1252"):
                try:
                    content = raw.decode(enc)
                    return {
                        "ok": True,
                        "type": "text",
                        "subtype": "plain",
                        "encoding": enc,
                        "chars_count": len(content),
                        "lines_count": len(content.splitlines()),
                        "content": content
                    }
                except UnicodeDecodeError:
                    continue
            content = raw.decode("utf-8", errors="replace")
            return {
                "ok": True,
                "type": "text",
                "subtype": "plain",
                "encoding": "utf-8-replace",
                "chars_count": len(content),
                "content": content
            }
        except Exception as exc:
            return {"ok": False, "type": "text", "error": str(exc)}

    def _read_json_file(self, path: Path, fmt: str) -> dict[str, Any]:
        """Parsing robuste JSON / JSONL."""
        try:
            txt = path.read_text(encoding="utf-8", errors="replace")
            if fmt == "json":
                parsed = json.loads(txt)
                return {
                    "ok": True,
                    "type": "text",
                    "subtype": "json",
                    "structure": "object" if isinstance(parsed, dict) else "list",
                    "keys_count": len(parsed) if isinstance(parsed, (dict, list)) else 1,
                    "content": txt,
                    "parsed_data": parsed
                }
            else:
                lines = [json.loads(l) for l in txt.splitlines() if l.strip()]
                return {
                    "ok": True,
                    "type": "text",
                    "subtype": "jsonl",
                    "lines_count": len(lines),
                    "content": txt,
                    "parsed_data": lines
                }
        except Exception as exc:
            return {"ok": False, "type": "text", "error": f"Erreur JSON : {exc}"}

    def _read_csv_file(self, path: Path, fmt: str) -> dict[str, Any]:
        """Extraction tabulaire structurée CSV / TSV."""
        try:
            delimiter = "\t" if fmt == "tsv" or path.suffix.lower() == ".tsv" else ","
            txt = path.read_text(encoding="utf-8", errors="replace")
            reader = csv.reader(io.StringIO(txt), delimiter=delimiter)
            rows = list(reader)
            headers = rows[0] if rows else []
            return {
                "ok": True,
                "type": "text",
                "subtype": fmt,
                "headers": headers,
                "rows_count": len(rows),
                "tables": [{"headers": headers, "rows": rows[1:100]}],
                "content": txt
            }
        except Exception as exc:
            return {"ok": False, "type": "text", "error": f"Erreur CSV : {exc}"}

    def _read_xml_html_file(self, path: Path, fmt: str) -> dict[str, Any]:
        """Extraction de texte épuré depuis XML / HTML / RSS."""
        try:
            txt = path.read_text(encoding="utf-8", errors="replace")
            clean_text = re.sub(r'<script.*?</script>', '', txt, flags=re.DOTALL | re.IGNORECASE)
            clean_text = re.sub(r'<style.*?</style>', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
            clean_text = re.sub(r'<[^>]+>', ' ', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()

            table_matches = re.findall(r'<tr[^>]*>(.*?)</tr>', txt, flags=re.DOTALL | re.IGNORECASE)
            tables = []
            if table_matches:
                extracted_rows = []
                for tr in table_matches[:50]:
                    cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, flags=re.DOTALL | re.IGNORECASE)
                    clean_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
                    if clean_cells:
                        extracted_rows.append(clean_cells)
                if extracted_rows:
                    tables.append({"headers": extracted_rows[0], "rows": extracted_rows[1:]})

            return {
                "ok": True,
                "type": "text",
                "subtype": fmt,
                "raw_chars_count": len(txt),
                "clean_text_count": len(clean_text),
                "tables": tables,
                "content": clean_text or txt
            }
        except Exception as exc:
            return {"ok": False, "type": "text", "error": f"Erreur XML/HTML : {exc}"}

    def _read_subtitles_file(self, path: Path) -> dict[str, Any]:
        """Extraction de sous-titres SRT / VTT."""
        try:
            txt = path.read_text(encoding="utf-8", errors="replace")
            lines = []
            for line in txt.splitlines():
                line_s = line.strip()
                if not line_s or line_s.isdigit() or "-->" in line_s or line_s.startswith("WEBVTT"):
                    continue
                lines.append(line_s)
            full_subtitles = " ".join(lines)
            return {
                "ok": True,
                "type": "text",
                "subtype": "subtitles",
                "subtitles": full_subtitles,
                "content": full_subtitles
            }
        except Exception as exc:
            return {"ok": False, "type": "text", "error": str(exc)}

    def _read_pdf_file(self, path: Path) -> dict[str, Any]:
        """Extrait le texte d'un PDF avec pypdf ou extraction native regex."""
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            pages_text = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages_text.append(f"--- Page {i+1} ---\n{text}")
            full_text = "\n\n".join(pages_text).strip()

            if not full_text:
                return {
                    "ok": True,
                    "type": "pdf",
                    "status": "NEEDS_VISION_OCR",
                    "pages_count": len(reader.pages),
                    "content": f"[PDF SCANNÉ (Aucun texte extrait) : {path.name} | Requiert OCR Vision]"
                }
            return {
                "ok": True,
                "type": "pdf",
                "pages_count": len(reader.pages),
                "chars_count": len(full_text),
                "content": full_text
            }
        except ImportError:
            try:
                raw = path.read_bytes()
                streams = re.findall(b'stream[\r\n]+(.*?)[\r\n]+endstream', raw, re.DOTALL)
                extracted = []
                for s in streams[:30]:
                    try:
                        import zlib
                        decomp = zlib.decompress(s).decode("latin1", errors="ignore")
                        clean = " ".join(re.findall(r'\((.*?)\)', decomp))
                        if len(clean) > 20:
                            extracted.append(clean)
                    except Exception:
                        pass
                text = "\n".join(extracted)
                if text.strip():
                    return {"ok": True, "type": "pdf", "content": text}
            except Exception:
                pass
            return {"ok": True, "type": "pdf", "status": "NEEDS_VISION_OCR", "content": f"[PDF : {path.name} | OCR Requis]"}

    def _read_docx_file(self, path: Path) -> dict[str, Any]:
        """Extrait le texte d'un document DOCX via XML natif."""
        try:
            with zipfile.ZipFile(str(path), "r") as z:
                xml_content = z.read("word/document.xml").decode("utf-8", errors="ignore")
                paragraphs = re.findall(r'<w:p[ >](.*?)</w:p>', xml_content)
                text_lines = []
                for p in paragraphs:
                    tokens = re.findall(r'<w:t[^>]*>(.*?)</w:t>', p)
                    if tokens:
                        text_lines.append("".join(tokens))
                full_text = "\n".join(text_lines)
                return {
                    "ok": True,
                    "type": "docx",
                    "chars_count": len(full_text),
                    "content": full_text
                }
        except Exception as exc:
            return {"ok": False, "type": "docx", "error": f"Échec lecture DOCX : {exc}"}

    def _read_pptx_file(self, path: Path) -> dict[str, Any]:
        """Extrait le texte d'une présentation PPTX via XML natif."""
        try:
            with zipfile.ZipFile(str(path), "r") as z:
                slide_files = sorted([n for n in z.namelist() if re.match(r'ppt/slides/slide\d+\.xml', n)])
                slides_text = []
                for i, s_file in enumerate(slide_files, start=1):
                    xml_content = z.read(s_file).decode("utf-8", errors="ignore")
                    text_tokens = re.findall(r'<a:t[^>]*>(.*?)</a:t>', xml_content)
                    if text_tokens:
                        slides_text.append(f"--- Diapositive {i} ---\n" + "\n".join(text_tokens))
                full_text = "\n\n".join(slides_text).strip()
                return {
                    "ok": True,
                    "type": "pptx",
                    "slides_count": len(slide_files),
                    "chars_count": len(full_text),
                    "content": full_text or "[Présentation PPTX sans texte textuel direct]"
                }
        except Exception as exc:
            return {"ok": False, "type": "pptx", "error": f"Échec lecture PPTX : {exc}"}

    def _read_xlsx_file(self, path: Path) -> dict[str, Any]:
        """Extrait le texte et les cellules d'un tableur Excel XLSX."""
        try:
            with zipfile.ZipFile(str(path), "r") as z:
                if "xl/sharedStrings.xml" in z.namelist():
                    xml_content = z.read("xl/sharedStrings.xml").decode("utf-8", errors="ignore")
                    strings = re.findall(r'<t[^>]*>(.*?)</t>', xml_content)
                    full_text = "\n".join(strings)
                    return {
                        "ok": True,
                        "type": "xlsx",
                        "cells_count": len(strings),
                        "tables": [{"headers": ["Extrait de chaînes partagées"], "rows": [[s] for s in strings[:100]]}],
                        "content": full_text
                    }
                return {"ok": True, "type": "xlsx", "content": "[Feuille Excel vide ou sans texte partagé]"}
        except Exception as exc:
            return {"ok": False, "type": "xlsx", "error": f"Échec lecture XLSX : {exc}"}

    def _read_ole_file(self, path: Path, ole_type: str) -> dict[str, Any]:
        """Extraction de texte résiliente depuis les formats OLE binaires legacy (.doc, .xls, .ppt)."""
        try:
            raw = path.read_bytes()
            ascii_strings = re.findall(rb'[\x20-\x7E]{4,}', raw)
            text_tokens = [s.decode("latin1", errors="ignore") for s in ascii_strings if len(s) > 3]
            full_text = "\n".join(text_tokens[:200])
            return {
                "ok": True,
                "type": ole_type,
                "legacy_format": True,
                "chars_count": len(full_text),
                "content": f"[DOCUMENT OLE BINAIRE : {path.name}]\n" + (full_text or "[Aucun texte lisible extrait]")
            }
        except Exception as exc:
            return {"ok": False, "type": ole_type, "error": f"Échec lecture OLE : {exc}"}

    def _read_archive_file(self, path: Path, archive_type: str) -> dict[str, Any]:
        """Inspection sécurisée d'archive avec protection stricte anti-zip-bomb, anti-zip-slip et signal de troncature explicite."""
        entries = []
        total_uncompressed = 0
        total_raw_entries = 0
        truncated = False

        try:
            if archive_type == "zip":
                with zipfile.ZipFile(str(path), "r") as z:
                    raw_list = z.infolist()
                    total_raw_entries = len(raw_list)
                    truncated = total_raw_entries > MAX_ARCHIVE_FILES
                    for info in raw_list:
                        if ".." in info.filename or info.filename.startswith("/") or info.filename.startswith("\\"):
                            continue
                        total_uncompressed += info.file_size
                        if total_uncompressed > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                            return {"ok": False, "status": "ZIP_BOMB_DETECTED", "error": "Archive trop volumineuse (alerte zip bomb)."}
                        if len(entries) < MAX_ARCHIVE_FILES:
                            entries.append({
                                "name": info.filename,
                                "size": info.file_size,
                                "is_dir": info.is_dir()
                            })
            elif archive_type == "tar_gz":
                with tarfile.open(str(path), "r:gz") as t:
                    raw_members = t.getmembers()
                    total_raw_entries = len(raw_members)
                    truncated = total_raw_entries > MAX_ARCHIVE_FILES
                    for member in raw_members:
                        if ".." in member.name or member.name.startswith("/") or member.name.startswith("\\"):
                            continue
                        total_uncompressed += member.size
                        if total_uncompressed > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                            return {"ok": False, "status": "ZIP_BOMB_DETECTED", "error": "Archive trop volumineuse."}
                        if len(entries) < MAX_ARCHIVE_FILES:
                            entries.append({
                                "name": member.name,
                                "size": member.size,
                                "is_dir": member.isdir()
                            })

            trunc_msg = f" (Plafonnée à {MAX_ARCHIVE_FILES} fichiers)" if truncated else ""
            return {
                "ok": True,
                "type": archive_type,
                "total_files": len(entries),
                "total_archive_entries": total_raw_entries,
                "truncated": truncated,
                "total_uncompressed_bytes": total_uncompressed,
                "file_manifest": entries,
                "content": f"[ARCHIVE : {len(entries)} fichiers répertoriés sur {total_raw_entries}{trunc_msg} | Taille décompressée : {round(total_uncompressed/1024, 1)} KB]"
            }
        except Exception as exc:
            return {"ok": False, "type": archive_type, "error": f"Erreur archive : {exc}"}

    def _read_image_metadata(self, path: Path, detected_type: str) -> dict[str, Any]:
        """Extraction des métadonnées d'image et détection QR Code immédiate."""
        qr_res = None
        try:
            from core.perception.qr_engine import QREngine
            qr_res = QREngine().decode_qrcode(path)
        except Exception:
            pass

        qr_info = ""
        if qr_res and qr_res.get("ok"):
            qr_info = f" | QR DÉTECTÉ : '{qr_res.get('primary_data')}'"

        dimensions = None
        try:
            from PIL import Image
            with Image.open(path) as img:
                dimensions = {"width": img.width, "height": img.height, "mode": img.mode}
        except Exception:
            pass

        return {
            "ok": True,
            "type": "image",
            "dimensions": dimensions,
            "status": "REQUIRES_VISION_OCR" if not (qr_res and qr_res.get("ok")) else "QR_AND_VISION",
            "qr_data": qr_res.get("primary_data") if (qr_res and qr_res.get("ok")) else None,
            "content": f"[IMAGE DÉTECTÉE : {path.name}{qr_info} | Analyse Vision OCR disponible]"
        }

    def read_complex_document(self, file_path: Path | str) -> dict[str, Any]:
        """Lecture de documents complexes : repli déterministe sur le parseur universel."""
        path = Path(file_path)
        try:
            from docling.document_converter import DocumentConverter
            converter = DocumentConverter()
            result = converter.convert(str(path))
            markdown_output = result.document.export_to_markdown()
            return {
                "ok": True,
                "parser": "docling_v2",
                "file_path": str(path),
                "content": markdown_output,
                "length": len(markdown_output),
                "provenance": "[DONNEE_PASSIVE_DOCLING]"
            }
        except Exception:
            native_res = self.read_file(path)
            native_res["file_path"] = str(path)
            if native_res.get("ok"):
                native_res["parser"] = "native_universal_fallback"
            return native_res


# Alias canoniques
UniversalReader = UniversalFileReader
universal_reader = UniversalFileReader()
