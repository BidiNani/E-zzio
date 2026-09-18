"""
Tests unitaires pour le moteur QR Code (génération, décodage OpenCV et aller-retour).
"""

import os

import pytest

from core.perception.qr_engine import QREngine
from core.perception.universal_reader import UniversalFileReader


def test_qr_roundtrip_encode_decode(tmp_path):
    qr_engine = QREngine(workspace_root=str(tmp_path))

    expected_payload = "https://github.com/BidiNani/E-zzio/releases/tag/v2.0"
    out_file = tmp_path / "projects" / "app" / "qr_test.png"

    # 1. Génération du QR code
    gen_res = qr_engine.generate_qrcode(data=expected_payload, output_path=out_file)
    assert gen_res["ok"] is True
    assert gen_res["status"] == "GENERATED"
    assert os.path.exists(gen_res["path"])

    # 2. Décodage déterministe immédiat via OpenCV
    dec_res = qr_engine.decode_qrcode(gen_res["path"])
    assert dec_res["ok"] is True
    assert dec_res["status"] == "QR_DETECTED"
    assert dec_res["primary_data"] == expected_payload


def test_universal_reader_qr_integration(tmp_path):
    qr_engine = QREngine(workspace_root=str(tmp_path))
    reader = UniversalFileReader()

    secret_message = "EZZIO_SOVEREIGN_NODE_READY_2026"
    qr_path = tmp_path / "outputs" / "secret_qr.png"
    qr_engine.generate_qrcode(data=secret_message, output_path=qr_path)

    # Lecture via le UniversalFileReader
    read_res = reader.read_file(qr_path)
    assert read_res["ok"] is True
    assert read_res["type"] == "image"
    assert read_res["qr_data"] == secret_message
    assert secret_message in read_res["content"]


def test_qr_empty_or_no_qr(tmp_path):
    qr_engine = QREngine(workspace_root=str(tmp_path))

    # Image PNG vierge sans QR code
    blank_path = tmp_path / "blank.png"
    import cv2
    import numpy as np
    blank_img = np.ones((200, 200, 3), dtype=np.uint8) * 255
    cv2.imwrite(str(blank_path), blank_img)

    dec_res = qr_engine.decode_qrcode(blank_path)
    assert dec_res["ok"] is False
    assert dec_res["status"] == "NO_QR_DETECTED"
