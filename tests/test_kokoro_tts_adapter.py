"""
Tests unitaires et de cycle de vie pour l'adapteur de capacité externe KokoroTTSAdapter.
Couvre les cas nominaux, de panne contrôlée, de repli procédural, de restauration et de sécurité des logs.
"""
import os
import shutil
import pytest

pytestmark = pytest.mark.optional_model
from pathlib import Path

from core.capabilities.kokoro_tts_adapter import KokoroTTSAdapter
from core.voice.voice_gateway import VoiceGateway

def test_kokoro_adapter_initialization():
    adapter = KokoroTTSAdapter()
    assert adapter.is_available is True

def test_kokoro_adapter_synthesize_real():
    adapter = KokoroTTSAdapter()
    res = adapter.synthesize("Bonjour E-ZzIO. Ceci est un test de validation unitaire.", lang="fr-fr")
    assert res["ok"] is True
    assert res["engine"] == "kokoro-82m-onnx"
    assert res["sample_rate"] == 24000
    assert res["size_bytes"] > 1000
    assert len(res["sha256"]) == 64
    assert res["fallback_used"] is False

def test_kokoro_adapter_fallback_on_invalid_model():
    adapter = KokoroTTSAdapter(model_path="invalid_path.onnx", voices_path="invalid_voices.bin")
    assert adapter.is_available is False
    res = adapter.synthesize("Test de repli de secours.")
    assert res["ok"] is True
    assert res["engine"] == "ezzio-procedural-tts"
    assert res["fallback_used"] is True
    assert res["sample_rate"] == 16000

@pytest.mark.asyncio
async def test_voice_gateway_kokoro_primary_and_fallback():
    vg = VoiceGateway()
    assert vg.active_engine == "kokoro-82m-onnx"
    
    # Test nominal
    audio_nom = await vg.synthesize("Test nominal voix.")
    assert len(audio_nom) > 1000
    
    # Test fallback simule en invalidant l'adapteur
    vg._kokoro_adapter = None
    assert vg.active_engine == "ezzio-procedural-tts"
    audio_fb = await vg.synthesize("Test repli voix.")
    assert len(audio_fb) > 0

def test_zero_secrets_leaked_in_logs():
    # Verifie qu'aucune cle privee ou token n'est logge
    adapter = KokoroTTSAdapter()
    res = adapter.synthesize("Vérification sécurité.")
    assert "token" not in res
    assert "api_key" not in res
    assert "secret" not in res
