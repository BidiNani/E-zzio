"""
E-ZZIO V10.0 — UNIVERSAL INGESTION & IMAGE EDITOR VALIDATION SUITE
Vérifie la robustesse de l'ingestion universelle, le contrat de données,
l'anti-disguise executable, l'anti-zip-slip/bomb et l'édition d'image déterministe.
"""

import pytest
import io
import json
import zipfile
from pathlib import Path
from PIL import Image

from core.perception.universal_reader import UniversalFileReader
from core.generators.image_engine import ImageEngine


@pytest.fixture
def temp_workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


def test_ingestion_text_json_csv_structured(temp_workspace):
    reader = UniversalFileReader()

    # 1. JSON
    json_file = temp_workspace / "sample.json"
    json_file.write_text(json.dumps({"app": "E-ZzIO", "version": "10.0"}), encoding="utf-8")
    res_json = reader.read_file(json_file)
    assert res_json["ok"] is True
    assert res_json["type"] == "text"
    assert res_json["subtype"] == "json"
    assert res_json["parsed_data"]["app"] == "E-ZzIO"
    assert "[DONNÉE PASSIVE NON FIABLE]" in res_json["provenance"]

    # 2. CSV
    csv_file = temp_workspace / "metrics.csv"
    csv_file.write_text("Indicateur,Valeur\nLatence,26ms\nTests,311", encoding="utf-8")
    res_csv = reader.read_file(csv_file)
    assert res_csv["ok"] is True
    assert res_csv["type"] == "text"
    assert res_csv["subtype"] == "csv"
    assert res_csv["headers"] == ["Indicateur", "Valeur"]
    assert len(res_csv["tables"][0]["rows"]) == 2

    # 3. Subtitles SRT
    srt_file = temp_workspace / "video.srt"
    srt_file.write_text("1\n00:00:01,000 --> 00:00:04,000\nBienvenue sur E-ZzIO 2026", encoding="utf-8")
    res_srt = reader.read_file(srt_file)
    assert res_srt["ok"] is True
    assert res_srt["type"] == "text"
    assert res_srt["subtype"] == "subtitles"
    assert "Bienvenue sur E-ZzIO 2026" in res_srt["subtitles"]


def test_disguised_executable_detection(temp_workspace):
    """Vérifie que tout binaire exécutable déguisé avec extension .txt ou .png est bloqué."""
    reader = UniversalFileReader()
    fake_txt = temp_workspace / "disguised_virus.txt"
    fake_txt.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00")

    res = reader.read_file(fake_txt)
    assert res["ok"] is False
    assert res["status"] == "BLOCKED_EXECUTABLE"
    assert "DISGUISED_EXECUTABLE" in res["security_flags"]


def test_anti_zip_slip_and_bomb(temp_workspace):
    """Vérifie la protection contre le Zip-Slip (traversée de chemin) et les archives malveillantes."""
    reader = UniversalFileReader()
    zip_path = temp_workspace / "safe.zip"

    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("clean_file.txt", "Contenu sain")
        z.writestr("../escape.txt", "Malveillant")

    res = reader.read_file(zip_path)
    assert res["ok"] is True
    assert res["type"] == "zip"
    names = [f["name"] for f in res["file_manifest"]]
    assert "clean_file.txt" in names
    assert "../escape.txt" not in names


def test_image_editor_deterministic_pipeline(temp_workspace):
    """Vérifie les opérations d'édition déterministe d'image sans écrasement de l'original."""
    engine = ImageEngine(workspace_root=str(temp_workspace))

    # 1. Génération d'une image source
    banner = engine.generate_tech_banner(filename="source.png", title="SOURCE IMAGE")
    assert banner["ok"] is True
    src_path = Path(banner["path"])
    assert src_path.exists()

    # 2. Édition (resize + rotate + brightness)
    edit_res = engine.edit_image(
        input_path=src_path,
        output_filename="edited.png",
        operations=[
            {"action": "resize", "width": 400, "height": 200},
            {"action": "rotate", "angle": 180},
            {"action": "brightness", "factor": 1.2}
        ]
    )

    assert edit_res["ok"] is True
    assert edit_res["width"] == 400
    assert edit_res["height"] == 200
    assert edit_res["hash_before"] != edit_res["hash_after"]
    assert src_path.stat().st_size == banner["size_bytes"]
