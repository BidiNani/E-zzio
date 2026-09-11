"""
E-ZZIO Test Suite — Universal Generation Gateway Certification.
Valide la passerelle multimodale par message en langage naturel :
- Compréhension d'intention sans spécification de format technique
- Vérification structurelle réelle de chaque fichier produit (XLSX, PPTX, PDF, DOCX, PNG, WAV, OBJ, ZIP, App)
- Confinement absolu dans outputs/ ou projects/ (zéro pollution de la racine)
- Gestion honnête et transparente de la limite matérielle (Vidéo / VRAM 4 Go)
"""
import pytest
import os
import wave
import zipfile
from pathlib import Path
from openpyxl import load_workbook
from docx import Document
from pptx import Presentation
from PIL import Image

from core.generators.generation_router import GenerationRouter
from core.perception.qr_engine import QREngine


@pytest.fixture
def router(tmp_path):
    return GenerationRouter(workspace_root=str(tmp_path))


@pytest.mark.asyncio
async def test_universal_routing_spreadsheet(router, tmp_path):
    msg = "Génère-moi un tableur de suivi budgétaire mensuel pour nos serveurs"
    res = await router.route_and_generate(msg)
    assert res["ok"] is True
    assert res["intent"] == "SPREADSHEET"
    
    file_path = Path(res["path"])
    assert file_path.exists()
    assert file_path.parent == tmp_path / "outputs"
    
    # Validation structurelle OpenXML XLSX
    wb = load_workbook(str(file_path), data_only=False)
    assert "Budget_Mensuel" in wb.sheetnames
    ws = wb["Budget_Mensuel"]
    assert ws["A1"].value == "Suivi Budgétaire"
    assert ws["A3"].value == "Poste"
    assert ws["D4"].value == "=B2-C2"


@pytest.mark.asyncio
async def test_universal_routing_presentation(router, tmp_path):
    msg = "Crée-moi une présentation de pitch sur la roadmap IA et l'architecture souveraine"
    res = await router.route_and_generate(msg)
    assert res["ok"] is True
    assert res["intent"] == "PRESENTATION"
    
    file_path = Path(res["path"])
    assert file_path.exists()
    assert file_path.parent == tmp_path / "outputs"
    
    # Validation structurelle PPTX
    prs = Presentation(str(file_path))
    assert len(prs.slides) == 3
    slide1_title = prs.slides[0].shapes.title.text
    assert "E-ZZIO" in slide1_title


@pytest.mark.asyncio
async def test_universal_routing_pdf(router, tmp_path):
    msg = "Fais-moi un rapport PDF officiel de certification système"
    res = await router.route_and_generate(msg)
    assert res["ok"] is True
    assert res["intent"] == "PDF"
    
    file_path = Path(res["path"])
    assert file_path.exists()
    assert file_path.parent == tmp_path / "outputs"
    assert res["size_bytes"] > 1000
    
    # Validation header PDF
    content = file_path.read_bytes()
    assert content.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_universal_routing_document(router, tmp_path):
    msg = "Génère un document Word avec le cahier des charges et spécifications techniques"
    res = await router.route_and_generate(msg)
    assert res["ok"] is True
    assert res["intent"] == "DOCUMENT"
    
    file_path = Path(res["path"])
    assert file_path.exists()
    assert file_path.parent == tmp_path / "outputs"
    
    # Validation structurelle DOCX
    doc = Document(str(file_path))
    assert len(doc.paragraphs) > 0
    assert len(doc.tables) == 1
    assert "Spécifications" in doc.paragraphs[0].text


@pytest.mark.asyncio
async def test_universal_routing_image(router, tmp_path):
    msg = "Génère une image de bannière tech cyberpunk pour la plateforme"
    res = await router.route_and_generate(msg)
    assert res["ok"] is True
    assert res["intent"] == "IMAGE"
    assert res["generation_time_ms"] > 0
    
    file_path = Path(res["path"])
    assert file_path.exists()
    assert file_path.parent == tmp_path / "outputs"
    
    # Validation format et dimensions d'image
    with Image.open(str(file_path)) as img:
        assert img.format == "PNG"
        assert img.size == (1200, 630)


@pytest.mark.asyncio
async def test_universal_routing_qr_code(router, tmp_path):
    msg = "Fais-moi un logo en QR code pointant vers https://e-zzio.ai/docs"
    res = await router.route_and_generate(msg)
    assert res["ok"] is True
    assert res["intent"] == "QR_CODE"
    assert "https://e-zzio.ai/docs" in res["data_encoded"]
    
    file_path = Path(res["path"])
    assert file_path.exists()
    assert file_path.parent == tmp_path / "outputs"


@pytest.mark.asyncio
async def test_universal_routing_archive(router, tmp_path):
    msg = "Fais-moi une archive zip de sauvegarde"
    res = await router.route_and_generate(msg)
    assert res["ok"] is True
    assert res["intent"] == "ARCHIVE"
    
    file_path = Path(res["path"])
    assert file_path.exists()
    assert zipfile.is_zipfile(str(file_path))


@pytest.mark.asyncio
async def test_universal_routing_audio(router, tmp_path):
    msg = "Synthétise un signal sonore audio à 440 Hz"
    res = await router.route_and_generate(msg)
    assert res["ok"] is True
    assert res["intent"] == "AUDIO"
    
    file_path = Path(res["path"])
    assert file_path.exists()
    with wave.open(str(file_path), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 44100


@pytest.mark.asyncio
async def test_universal_routing_3d(router, tmp_path):
    msg = "Génère un modèle 3D de cube pour le moteur Godot"
    res = await router.route_and_generate(msg)
    assert res["ok"] is True
    assert res["intent"] == "3D_MESH"
    
    file_path = Path(res["path"])
    assert file_path.exists()
    content = file_path.read_text(encoding="utf-8")
    assert "v " in content
    assert "f " in content


@pytest.mark.asyncio
async def test_universal_routing_dev_studio(router, tmp_path):
    msg = "Code-moi un jeu de snake en Python"
    res = await router.route_and_generate(msg)
    assert res["ok"] is True
    assert res["intent"] == "DEV_STUDIO"
    assert res["project_name"] == "snake_game"
    assert (tmp_path / "projects" / "snake_game").exists()


@pytest.mark.asyncio
async def test_universal_routing_video_unsupported(router):
    msg = "Génère-moi une vidéo d'animation 4K de présentation"
    res = await router.route_and_generate(msg)
    assert res["ok"] is False
    assert res["intent"] == "VIDEO"
    assert res["status"] == "UNSUPPORTED_HARDWARE_LIMIT"
    assert "CPU pur, 4 Go VRAM" in res["message"]


@pytest.mark.asyncio
async def test_universal_routing_image_generative_ai(router):
    msg = "Génère une image IA d'un paysage futuriste avec Nano Banana"
    res = await router.route_and_generate(msg)
    assert res["ok"] is True
    assert res["intent"] == "IMAGE"
    assert res["tier"] == "CLOUD_GENERATIVE_AI"
    assert "Nano Banana" in res["codename"]


@pytest.mark.asyncio
async def test_outputs_confinement_integrity(router, tmp_path):
    # Exécution multiple
    await router.route_and_generate("Fais un tableur budget")
    await router.route_and_generate("Génère une présentation")
    await router.route_and_generate("Fais un rapport PDF")
    await router.route_and_generate("Génère une bannière image")
    
    outputs_files = list((tmp_path / "outputs").glob("*"))
    assert len(outputs_files) >= 4
    
    # Vérifier qu'aucun fichier généré n'est à la racine de tmp_path
    root_files = [f for f in tmp_path.iterdir() if f.is_file()]
    assert len(root_files) == 0
