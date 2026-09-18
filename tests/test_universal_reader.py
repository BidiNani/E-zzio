"""
Tests unitaires pour l'UniversalFileReader d'E-ZzIO.
"""

import os
import zipfile

import pytest

from core.perception.universal_reader import UniversalFileReader


def test_universal_reader_text_and_json(tmp_path):
    reader = UniversalFileReader()

    # 1. Fichier texte simple
    txt_file = tmp_path / "document.txt"
    txt_file.write_text("Données d'analyse confidentielles.", encoding="utf-8")
    res_txt = reader.read_file(txt_file)
    assert res_txt["ok"] is True
    assert res_txt["type"] == "text"
    assert "Données d'analyse" in res_txt["content"]

    # 2. Fichier JSON
    json_file = tmp_path / "data.json"
    json_file.write_text('{"cle": "valeur"}', encoding="utf-8")
    res_json = reader.read_file(json_file)
    assert res_json["ok"] is True
    assert res_json["type"] == "text"


def test_universal_reader_magic_bytes_detection(tmp_path):
    reader = UniversalFileReader()

    # 1. Faux fichier PNG (signature PNG réelle)
    png_file = tmp_path / "fake_name.dat"
    png_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR...")
    res_png = reader.read_file(png_file)
    assert res_png["ok"] is True
    assert res_png["type"] == "image"
    assert res_png["status"] == "REQUIRES_VISION_OCR"

    # 2. Fichier PDF
    pdf_file = tmp_path / "doc.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n%...\n")
    res_pdf = reader.read_file(pdf_file)
    assert res_pdf["ok"] is True
    assert "pdf" in res_pdf["type"]


def test_universal_reader_zip_archive(tmp_path):
    reader = UniversalFileReader()

    zip_path = tmp_path / "archive.zip"
    with zipfile.ZipFile(str(zip_path), "w") as z:
        z.writestr("test1.txt", "Contenu fichier 1")
        z.writestr("test2.txt", "Contenu fichier 2")

    res_zip = reader.read_file(zip_path)
    assert res_zip["ok"] is True
    assert res_zip["type"] == "zip"
    assert res_zip["total_files"] == 2
    assert len(res_zip["file_manifest"]) == 2


def test_universal_reader_unsupported_format(tmp_path):
    reader = UniversalFileReader()

    # Fichier binaire inconnu
    bin_file = tmp_path / "mystery.bin"
    bin_file.write_bytes(b"\x00\x01\x02\x03\x04\x05\x06\x07")
    res_bin = reader.read_file(bin_file)
    assert res_bin["ok"] is False
    assert res_bin["status"] == "UNSUPPORTED_FORMAT"
