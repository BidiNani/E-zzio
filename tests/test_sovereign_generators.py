"""
E-ZZIO Test Suite — Sovereign Multimodal Generators Certification.
Certifie les générateurs locaux XLSX, DOCX, ZIP sécurisé (Anti-Zip Slip), Audio WAV et Maillages 3D OBJ.
"""
import os
import zipfile
from pathlib import Path

import pytest

from core.generators.archive_engine import ArchiveEngine, ArchiveSecurityError
from core.generators.doc_engine import DocEngine
from core.generators.media_engine import MediaEngine
from core.generators.sheet_engine import SheetEngine


def test_sheet_engine_generation_with_formulas(tmp_path):
    engine = SheetEngine(workspace_root=str(tmp_path))
    sheets_data = [
        {
            "sheet_name": "Télémétrie",
            "headers": ["Service", "Latence (ms)", "Disponibilité", "Statut"],
            "rows": [
                ["Gateway", 1095, 0.999, "OK"],
                ["SQLite FTS5", 3.7, 1.0, "OK"],
                ["Ollama Health", 0.05, 1.0, "OPTIONAL"],
            ],
            "totals": ["Moyenne", "=AVERAGE(B2:B4)", "=AVERAGE(C2:C4)", "OPERATIONNEL"]
        }
    ]

    res = engine.generate_spreadsheet("telemetry_report.xlsx", sheets_data, title="Rapport E-ZZIO")
    assert res["ok"] is True
    assert os.path.exists(res["path"])
    assert res["filename"] == "telemetry_report.xlsx"
    assert res["size_bytes"] > 0
    assert "Télémétrie" in res["sheets"]


def test_doc_engine_generation_with_tables(tmp_path):
    engine = DocEngine(workspace_root=str(tmp_path))
    sections = [
        {"type": "heading", "level": 1, "text": "1. Architecture Souveraine"},
        {"type": "paragraph", "text": "Le système E-ZZIO opère de manière entièrement autonome et résiliente."},
        {"type": "bullet", "items": ["Confinement strict", "Zéro blocage réseau", "Multi-projets"]},
        {
            "type": "table",
            "headers": ["Module", "Rôle", "Statut"],
            "rows": [["CognitiveGateway", "Routage cognitif", "Actif"], ["GeminiPool", "Rotation multi-projets", "Actif"]]
        }
    ]

    res = engine.generate_docx("architecture_spec.docx", "Spécification Système", sections)
    assert res["ok"] is True
    assert os.path.exists(res["path"])
    assert res["filename"] == "architecture_spec.docx"
    assert res["size_bytes"] > 0


def test_archive_engine_zip_creation_and_safe_extraction(tmp_path):
    engine = ArchiveEngine(workspace_root=str(tmp_path))

    # Création de fichiers sources
    src_dir = tmp_path / "sources"
    src_dir.mkdir()
    (src_dir / "test1.txt").write_text("Hello E-ZZIO", encoding="utf-8")
    (src_dir / "test2.json").write_text('{"status": "ok"}', encoding="utf-8")

    # 1. Création de l'archive
    res_zip = engine.create_zip("backup.zip", [str(src_dir / "test1.txt"), str(src_dir / "test2.json")], base_dir=str(src_dir))
    assert res_zip["ok"] is True
    assert os.path.exists(res_zip["path"])
    assert res_zip["total_files"] == 2

    # 2. Extraction sécurisée
    extract_dest = tmp_path / "extracted"
    res_ext = engine.safe_extract_zip(res_zip["path"], str(extract_dest))
    assert res_ext["ok"] is True
    assert res_ext["extracted_count"] == 2
    assert (extract_dest / "test1.txt").exists()
    assert (extract_dest / "test2.json").exists()


def test_archive_engine_anti_zip_slip_rejection(tmp_path):
    engine = ArchiveEngine(workspace_root=str(tmp_path))

    # Fabrication d'un ZIP piégé avec tentative d'évasion parent (Zip Slip)
    evil_zip_path = tmp_path / "evil.zip"
    with zipfile.ZipFile(str(evil_zip_path), "w") as zf:
        zf.writestr("../../system_escape.txt", "MALICIOUS PAYLOAD")

    extract_dest = tmp_path / "sandbox"

    with pytest.raises(ArchiveSecurityError) as exc_info:
        engine.safe_extract_zip(str(evil_zip_path), str(extract_dest))

    assert "Anti-Zip Slip" in str(exc_info.value)
    assert not (tmp_path / "system_escape.txt").exists()


def test_media_engine_wav_tone_and_3d_obj_generation(tmp_path):
    engine = MediaEngine(workspace_root=str(tmp_path))

    # 1. Génération audio WAV
    res_audio = engine.generate_tone_wav("ping.wav", frequency_hz=880.0, duration_sec=0.2)
    assert res_audio["ok"] is True
    assert os.path.exists(res_audio["path"])
    assert res_audio["size_bytes"] > 0
    assert res_audio["duration_sec"] == 0.2

    # 2. Génération 3D OBJ
    res_3d = engine.generate_3d_cube_obj("cube.obj", size=2.0, color_name="NeonBlue")
    assert res_3d["ok"] is True
    assert os.path.exists(res_3d["path"])
    assert res_3d["vertices_count"] == 8
    assert res_3d["faces_count"] == 12
    content = Path(res_3d["path"]).read_text(encoding="utf-8")
    assert "v 1.0000 1.0000 1.0000" in content
    assert "f 1 2 3" in content
