"""
Tests unitaires pour le VisionEngine d'E-ZzIO.
"""

import pytest

from core.perception.vision_engine import VisionEngine


def test_vision_engine_base64_encoding(tmp_path):
    engine = VisionEngine()

    # Création d'une fausse image PNG
    test_img = tmp_path / "test.png"
    test_img.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR...")

    b64 = engine._encode_image_base64(test_img)
    assert b64 is not None
    assert len(b64) > 10


@pytest.mark.asyncio
async def test_vision_engine_offline_resilience(tmp_path):
    # Port inexistant pour tester la résilience réseau sans crash
    engine = VisionEngine(ollama_url="http://127.0.0.1:59999")

    test_img = tmp_path / "screenshot.png"
    test_img.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR...")

    res = await engine.describe_image(test_img)
    assert res["ok"] is False
    assert res["status"] in ("OLLAMA_OFFLINE", "EXCEPTION")

    res_ocr = await engine.extract_ocr_text(test_img)
    assert res_ocr["ok"] is False
