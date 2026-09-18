"""
E-ZZIO API — Sovereign Multimodal Generators Router.
Expose les endpoints de génération multimodale locale (XLSX, DOCX, PPTX, PDF, ZIP, Audio, 3D, Image)
et la passerelle universelle de routage par message naturel (/generators/universal).
"""
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.generators import (
    ArchiveEngine,
    DocEngine,
    GenerationRouter,
    ImageEngine,
    MediaEngine,
    PdfEngine,
    SheetEngine,
    SlideEngine,
)

router = APIRouter(prefix="/generators", tags=["generators"])

_sheet_engine = SheetEngine()
_doc_engine = DocEngine()
_slide_engine = SlideEngine()
_pdf_engine = PdfEngine()
_image_engine = ImageEngine()
_archive_engine = ArchiveEngine()
_media_engine = MediaEngine()
_generation_router = GenerationRouter()


class UniversalGenerateRequest(BaseModel):
    message: str = Field(..., example="génère-moi un tableur de suivi budgétaire")


class XLSXGenerateRequest(BaseModel):
    filename: str = Field(..., example="rapport_financier.xlsx")
    title: str | None = Field(None, example="Bilan Opérationnel Q1 2026")
    sheets: list[dict[str, Any]] = Field(..., example=[{
        "sheet_name": "Performance",
        "headers": ["Indicateur", "Valeur", "Cible"],
        "rows": [["Latence (ms)", 1095, 1500], ["Tests Verts", 237, 237]]
    }])


class DOCXGenerateRequest(BaseModel):
    filename: str = Field(..., example="synthese_architecture.docx")
    title: str = Field(..., example="Spécification Technique E-ZZIO")
    sections: list[dict[str, Any]] = Field(...)
    author: str | None = "E-ZZIO Autonomous Core"


class PPTXGenerateRequest(BaseModel):
    filename: str = Field(..., example="presentation_stratégique.pptx")
    title: str = Field(..., example="E-ZZIO Architecture 2.0")
    subtitle: str | None = Field(None, example="Plateforme d'IA Souveraine")
    slides: list[dict[str, Any]] | None = None
    author: str | None = "E-ZZIO Autonomous Core"


class PDFGenerateRequest(BaseModel):
    filename: str = Field(..., example="rapport_certification.pdf")
    title: str = Field(..., example="Rapport de Certification")
    sections: list[dict[str, Any]] = Field(...)
    author: str | None = "E-ZZIO Autonomous Core"


class ImageBannerRequest(BaseModel):
    filename: str = Field(..., example="banniere_tech.png")
    title: str = Field(..., example="E-ZZIO SYSTEM")
    subtitle: str | None = Field(None, example="Passerelle Universelle")
    width: int = 1200
    height: int = 630


class ZIPGenerateRequest(BaseModel):
    archive_name: str = Field(..., example="export_projet.zip")
    source_paths: list[str] = Field(...)


class AudioToneRequest(BaseModel):
    filename: str = Field(..., example="signal_ok.wav")
    frequency_hz: float = 440.0
    duration_sec: float = 0.5


class Mesh3DRequest(BaseModel):
    filename: str = Field(..., example="cube_repere.obj")
    size: float = 1.0
    color_name: str = "CyberCyan"


@router.post("/universal")
async def generate_universal(req: UniversalGenerateRequest) -> dict[str, Any]:
    """Passerelle universelle : interprète le message naturel et route vers le générateur adéquat."""
    try:
        return await _generation_router.route_and_generate(user_message=req.message)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/xlsx")
def generate_xlsx(req: XLSXGenerateRequest) -> dict[str, Any]:
    try:
        return _sheet_engine.generate_workbook(
            filename=req.filename,
            sheets_data=req.sheets,
            title=req.title
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/docx")
def generate_docx(req: DOCXGenerateRequest) -> dict[str, Any]:
    try:
        return _doc_engine.generate_document(
            filename=req.filename,
            title=req.title,
            sections=req.sections,
            author=req.author or "E-ZZIO Autonomous Core"
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/pptx")
def generate_pptx(req: PPTXGenerateRequest) -> dict[str, Any]:
    try:
        return _slide_engine.generate_presentation(
            filename=req.filename,
            title=req.title,
            subtitle=req.subtitle,
            slides_data=req.slides,
            author=req.author or "E-ZZIO Autonomous Core"
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/pdf")
def generate_pdf(req: PDFGenerateRequest) -> dict[str, Any]:
    try:
        return _pdf_engine.generate_pdf(
            filename=req.filename,
            title=req.title,
            sections=req.sections,
            author=req.author or "E-ZZIO Autonomous Core"
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


class ImageEditRequest(BaseModel):
    input_path: str = Field(..., example="outputs/banniere_tech.png")
    output_filename: str = Field(..., example="banniere_edited.png")
    operations: list[dict[str, Any]] = Field(..., example=[
        {"action": "resize", "width": 800, "height": 400},
        {"action": "rotate", "angle": 90}
    ])


@router.post("/image/banner")
def generate_image_banner(req: ImageBannerRequest) -> dict[str, Any]:
    try:
        return _image_engine.generate_tech_banner(
            filename=req.filename,
            title=req.title,
            subtitle=req.subtitle,
            width=req.width,
            height=req.height
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/image/edit")
def edit_image_endpoint(req: ImageEditRequest) -> dict[str, Any]:
    try:
        return _image_engine.edit_image(
            input_path=req.input_path,
            output_filename=req.output_filename,
            operations=req.operations
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/zip")
def generate_zip(req: ZIPGenerateRequest) -> dict[str, Any]:
    try:
        return _archive_engine.create_archive(
            archive_name=req.archive_name,
            files=req.source_paths
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/audio/tone")
def generate_audio_tone(req: AudioToneRequest) -> dict[str, Any]:
    try:
        return _media_engine.generate_audio_tone(
            filename=req.filename,
            frequency_hz=req.frequency_hz,
            duration_sec=req.duration_sec
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/3d/cube")
def generate_3d_cube(req: Mesh3DRequest) -> dict[str, Any]:
    try:
        return _media_engine.generate_3d_cube(
            filename=req.filename,
            size=req.size
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
