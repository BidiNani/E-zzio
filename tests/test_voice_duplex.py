"""
Tests unitaires pour le moteur vocal Duplex et l'interruption en temps réel (Barge-in).
"""

import asyncio
import struct
import time

import pytest

from core.voice.voice_duplex_engine import DuplexState, VoiceDuplexEngine


def test_vad_speech_detection():
    engine = VoiceDuplexEngine(energy_threshold=400)

    # 1. Silence (échantillons à 0)
    silence = struct.pack("<" + "h" * 1600, *([0] * 1600))
    assert engine.detect_voice_activity(silence) is False

    # 2. Voix / Son fort (amplitude élevée)
    voice_chunk = struct.pack("<" + "h" * 1600, *([2500] * 1600))
    assert engine.detect_voice_activity(voice_chunk) is True


@pytest.mark.asyncio
async def test_barge_in_instantaneous_interruption_and_context():
    engine = VoiceDuplexEngine()

    segments = ["Bonjour,", "je suis", "en train de vous", "expliquer la solution", "en détail..."]

    # 1. Démarrage de la lecture TTS en tâche de fond
    tts_task = asyncio.create_task(engine.simulate_tts_speech(segments, delay_per_segment=0.2))
    await asyncio.sleep(0.3)  # Laisse le temps de prononcer les 2 premiers segments

    assert engine.state == DuplexState.SPEAKING

    # 2. Déclenchement de l'interruption (Barge-in de l'utilisateur)
    start_t = time.perf_counter()
    barge_res = engine.trigger_barge_in()
    interruption_delay_ms = (time.perf_counter() - start_t) * 1000

    await tts_task

    # 3. Vérification de la latence (< 50ms) et de l'état
    assert barge_res["ok"] is True
    assert barge_res["status"] == "INTERRUPTED"
    assert interruption_delay_ms < 50.0  # Coupure immédiate en sous-50ms

    # 4. Vérification de la conservation du contexte prononcé
    history = engine._conversation_history
    assert len(history) == 1
    assert "Bonjour," in history[0]["content"]
    assert "[interrompu]" in history[0]["content"]
    # Vérifie que les derniers segments n'ont pas été ajoutés inutilement
    assert "en détail..." not in history[0]["content"]
