"""
tests/test_universal_input_access.py — Deterministic Multimodal Extraction Unit Tests
"""
import os

import pytest

from core.agent.capability_manager import CapabilityManager
from core.agent.input_access_manager import (
    InputAccessManager,
    InputDocument,
    InputType,
    input_access_manager,
)


def test_multimodal_classification():
    iam = InputAccessManager()

    assert iam.classify_input("https://ai.google.dev/docs") == InputType.URL
    assert iam.classify_input("sample.pdf") == InputType.PDF
    assert iam.classify_input("sample.png") == InputType.IMAGE
    assert iam.classify_input("sample.wav") == InputType.AUDIO
    assert iam.classify_input("sample.mp4") == InputType.VIDEO
    assert iam.classify_input("sample.zip") == InputType.ARCHIVE

def test_local_file_text_extraction():
    iam = InputAccessManager()
    doc = iam.acquire_and_extract(r"G:\AI\E-zzio\pyproject.toml")

    assert doc.status == "READY"
    assert doc.input_type == InputType.LOCAL_FILE
    assert len(doc.content_text) > 0

def test_image_visual_reference_extraction():
    iam = InputAccessManager()

    # Fixture image factice
    doc = iam.acquire_and_extract(r"G:\AI\E-zzio\pyproject.toml")
    doc_img = iam._extract_image(r"G:\AI\E-zzio\pyproject.toml")

    assert doc_img.status == "READY"
    assert doc_img.input_type == InputType.IMAGE
    assert doc_img.binary_reference is not None
    assert len(doc_img.visual_references) == 1
    assert "format" in doc_img.visual_references[0]

def test_audio_multimedia_extraction():
    iam = InputAccessManager()

    doc_audio = iam._extract_audio(r"G:\AI\E-zzio\pyproject.toml")
    assert doc_audio.status == "READY"
    assert doc_audio.input_type == InputType.AUDIO
    assert doc_audio.binary_reference is not None
    assert "duration_sec" in doc_audio.extracted_data

def test_video_multimedia_extraction():
    iam = InputAccessManager()

    doc_video = iam._extract_video(r"G:\AI\E-zzio\pyproject.toml")
    assert doc_video.status == "READY"
    assert doc_video.input_type == InputType.VIDEO
    assert doc_video.binary_reference is not None

def test_normalization_schema():
    doc = InputDocument(
        source="test.png",
        input_type=InputType.IMAGE,
        status="READY",
        content_text="[IMAGE MULTIMODALE]",
        binary_reference="test.png",
        visual_references=[{"format": "png"}],
        extracted_data={"resolution": "1920x1080"},
        metadata={"size": 1024}
    )

    assert doc.source == "test.png"
    assert doc.binary_reference == "test.png"
    assert len(doc.visual_references) == 1
    assert doc.extracted_data["resolution"] == "1920x1080"

if __name__ == "__main__":
    test_multimodal_classification()
    test_local_file_text_extraction()
    test_image_visual_reference_extraction()
    test_audio_multimedia_extraction()
    test_video_multimedia_extraction()
    test_normalization_schema()
    print("✅ ALL MULTIMODAL EXTRACTION TESTS PASSED")
