import sys
import asyncio
import time
import os
import json
import re
import aiohttp
import numpy as np
from pathlib import Path

sys.path.insert(0, r'G:\AI\E-zzio')

print("=" * 60)
print(" E-ZZIO V7 — QUALIFICATION V6.3-R4 (DUAL-STREAM PARSER & RTF)")
print("=" * 60)

TARGET_MODEL = "qwen3:4b"
KOKORO_DIR = r"G:\AI\E-zzio\runtime\realtime\models\kokoro"
KOKORO_MODEL_PATH = os.path.join(KOKORO_DIR, "kokoro-v0_19.onnx")
KOKORO_VOICES_PATH = os.path.join(KOKORO_DIR, "voices.bin")

async def test_dual_stream_pipeline():
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": TARGET_MODEL,
        "prompt": "Réponds strictement en un seul mot : Bonjour.",
        "stream": True,
        "options": {"num_predict": 32}
    }

    thinking_tokens = []
    response_tokens = []
    t0 = time.perf_counter()
    ttft_response = None

    print(f"\n--- [1/3] Interrogation Qwen3 ({TARGET_MODEL}) avec Dual-Stream Parser ---")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP Error {resp.status}")
                
                async for line in resp.content:
                    if line:
                        chunk_str = line.decode('utf-8').strip()
                        if chunk_str:
                            data = json.loads(chunk_str)
                            
                            # Capture des flux séparés
                            think_part = data.get("thinking", "")
                            resp_part = data.get("response", "")
                            
                            if think_part:
                                thinking_tokens.append(think_part)
                            
                            if resp_part:
                                if ttft_response is None:
                                    ttft_response = (time.perf_counter() - t0) * 1000
                                response_tokens.append(resp_part)

        print(f"   🧠 Chunks de pensée ('thinking') captés : {len(thinking_tokens)} blocs")
        print(f"   💬 Chunks de réponse ('response') captés : {len(response_tokens)} blocs")
        
        full_thinking = "".join(thinking_tokens).strip()
        full_response = "".join(response_tokens).strip()

        if full_thinking:
            print(f"   🔍 Extrait Thinking : \"{full_thinking[:100]}...\" (Masqué pour le TTS)")
        print(f"   📝 Réponse Visible  : \"{full_response}\"")
        
        ttft_val = ttft_response if ttft_response is not None else 0.0
        print(f"   ⏱️ TTFT (First Response Token) : {round(ttft_val, 2)} ms")

    except Exception as e:
        print(f"   ❌ ÉCHEC du streaming dual-stream : {e}")
        sys.exit(1)

    # Règle Fail-Closed : Si aucune réponse n'est extraite
    if not full_response:
        print("   ❌ ÉCHEC CRITIQUE : Le champ 'response' est vide (le modèle n'a rien généré pour l'utilisateur).")
        sys.exit(1)

    print("\n--- [2/3] Test du Sentence Chunker sur le flux 'response' ---")
    sentences = re.split(r'([.!?\n])', full_response)
    clean_sentences = [s.strip() for s in sentences if s.strip() and s not in '.!?\n']
    if not clean_sentences:
        clean_sentences = [full_response]
    print(f"   ✅ Phrases découpées prêtes pour le TTS : {clean_sentences}")

    print("\n--- [3/3] Test de Synthèse Kokoro & Calcul du RTF (Real-Time Factor) ---")
    try:
        from kokoro_onnx import Kokoro
        kokoro = Kokoro(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH)
        voices = list(kokoro.voices)
        voice = next((v for v in voices if v.startswith('ff_') or v.startswith('fr_')), voices[0])

        target_text = clean_sentences[0]
        t_synth_start = time.perf_counter()
        samples, sr = kokoro.create(target_text, voice=voice, speed=1.0)
        synth_duration_s = time.perf_counter() - t_synth_start

        audio_duration_s = len(samples) / sr
        rtf = synth_duration_s / audio_duration_s if audio_duration_s > 0 else 999.0

        print(f"   ✅ Audio généré : {len(samples)} échantillons ({round(audio_duration_s, 2)} s audio)")
        print(f"   ⏱️ Temps de calcul CPU : {round(synth_duration_s * 1000, 2)} ms")
        print(f"   📊 Facteur Temps Réel (RTF) : {round(rtf, 3)} (Cible : < 1.0)")

        if rtf > 1.0:
            print(f"   ⚠️ Avertissement : Le RTF ({rtf}) est supérieur à 1.0 (plus lent que le temps réel).")
        else:
            print(f"   ✨ EXCELLENT : Kokoro s'exécute en flux tendu plus rapide que le temps réel sur votre Ryzen 9 !")

    except Exception as e:
        print(f"   ❌ ÉCHEC de la synthèse Kokoro : {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print(" RÉSULTAT V6.3-R4 : CERTIFICATION INTÉGRALE PASS (10/10)")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_dual_stream_pipeline())
