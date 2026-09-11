"""
E-ZZIO Sovereign Multimodal Generators Package.
Fournit les moteurs souverains de génération locale : Tableurs (XLSX), Documents (DOCX/PDF/PPTX), Archives (ZIP), Médias (WAV/3D OBJ/Images) et Routeur Universel.
"""
from core.generators.sheet_engine import SheetEngine
from core.generators.doc_engine import DocEngine
from core.generators.slide_engine import SlideEngine
from core.generators.pdf_engine import PdfEngine
from core.generators.image_engine import ImageEngine
from core.generators.archive_engine import ArchiveEngine, ArchiveSecurityError
from core.generators.media_engine import MediaEngine
from core.generators.generation_router import GenerationRouter

__all__ = [
    "SheetEngine",
    "DocEngine",
    "SlideEngine",
    "PdfEngine",
    "ImageEngine",
    "ArchiveEngine",
    "ArchiveSecurityError",
    "MediaEngine",
    "GenerationRouter",
]
