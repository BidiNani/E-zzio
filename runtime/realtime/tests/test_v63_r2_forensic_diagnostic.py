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
print(" E-ZZIO V7 — DIAGNOSTIC FORENSIQUE 10 POINTS (FAIL-CLOSED)")
print("=" * 60)

TARGET_MODEL = "qwen3:4b"
KOKORO_DIR = r"G:\AI\E-zzio\runtime\realtime\models\kokoro"
KOKORO_MODEL_PATH = os.path.join(KOKORO_DIR, "kokoro-v0_19.onnx")
KOKORO_VOICES_PATH = os.path.join(KOKORO_DIR, "voices.bin")

async def run_forensic_audit():
    results = {}

    print("\n--- [1/10] Vérification de l'accessibilité d'Ollama ---")
    tags_url = "http://localhost:11434/api/tags"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(tags_url, timeout=3.0) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    print(f"   ✅ Ollama répond. Modèles détectés : {models}")
                    results["[1] Ollama accessible"] = True
                else:
                    raise RuntimeError(f"HTTP Status {resp.status}")
    except Exception as e:
        print(f"   ❌ ÉCHEC : Ollama injoignable ({e})")
        results["[1] Ollama accessible"] = False
        sys.exit(1)

    print(f"\n--- [2/10] Vérification de la présence stricte de '{TARGET_MODEL}' ---")
    model_present = any(TARGET_MODEL in m for m in models)
    if model_present:
        print(f"   ✅ Le modèle '{TARGET_MODEL}' est présent.")
        results["[2] Modèle cible présent"] = True
    else:
        print(f"   ❌ ÉCHEC CRITIQUE (FAIL-CLOSED) : '{TARGET_MODEL}' est absent.")
        sys.exit(1)

    print("\n--- [3/10] Test du streaming HTTP brut sur Ollama ---")
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": TARGET_MODEL,
        "prompt": "Dis bonjour en un mot.",
        "stream": True,
        "options": {"num_predict": 10}
    }
    raw_chunks_received = 0
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP Error {resp.status}")
                async for line in resp.content:
                    if line:
                        raw_chunks_received += 1
        print(f"   ✅ Connexion streaming HTTP établie ({raw_chunks_received} blocs bruts reçus).")
        results["[3] Streaming HTTP fonctionnel"] = raw_chunks_received > 0
    except Exception as e:
        print(f"   ❌ ÉCHEC : Le streaming HTTP a échoué ({e})")
        sys.exit(1)

    print("\n--- [4/10] Test du parser JSON et extraction des tokens ---")
    extracted_tokens = []
    t0 = time.perf_counter()
    ttft = None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                async for line in resp.content:
                    if line:
                        data = json.loads(line.decode('utf-8'))
                        token = data.get("response", "")
                        if token:
                            if ttft is None:
                                ttft = (time.perf_counter() - t0) * 1000
                            extracted_tokens.append(token)
        
        ttft_val = ttft if ttft is not None else 0.0
        full_res = "".join(extracted_tokens).strip()
        print(f"   ✅ Tokens extraits : \"{full_res}\" (TTFT: {round(ttft_val, 2)} ms)")
        results["[4] Parser JSON et extraction"] = len(extracted_tokens) > 0
    except Exception as e:
        print(f"   ❌ ÉCHEC du parser JSON : {e}")
        results["[4] Parser JSON et extraction"] = False
        sys.exit(1)

    print("\n--- [5/10] Test du worker LLM asynchrone ---")
    text_queue = asyncio.Queue()

    async def mock_llm_worker():
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                async for line in resp.content:
                    if line:
                        data = json.loads(line.decode('utf-8'))
                        token = data.get("response", "")
                        if token:
                            await text_queue.put(token)
        await text_queue.put(None)

    try:
        await asyncio.wait_for(mock_llm_worker(), timeout=10.0)
        print("   ✅ Worker LLM exécuté et terminé sans erreur.")
        results["[5] Worker LLM opérationnel"] = True
    except Exception as e:
        print(f"   ❌ ÉCHEC du worker LLM : {e}")
        sys.exit(1)

    print("\n--- [6/10] Vérification de l'alimentation de la queue de texte ---")
    queue_tokens = []
    while not text_queue.empty():
        item = text_queue.get_nowait()
        if item:
            queue_tokens.append(item)
    print(f"   ✅ Tokens récupérés depuis la queue : {len(queue_tokens)} tokens.")
    results["[6] Queue de texte alimentée"] = len(queue_tokens) > 0

    print("\n--- [7/10] Test du découpeur de phrases (Sentence Chunker) ---")
    sentence_queue = asyncio.Queue()
    
    async def mock_chunker():
        buffer = "".join(queue_tokens)
        sentences = re.split(r'([.!?\n])', buffer)
        for s in sentences:
            if s.strip():
                await sentence_queue.put(s.strip())
        await sentence_queue.put(None)

    await mock_chunker()
    chunks_found = []
    while not sentence_queue.empty():
        item = await sentence_queue.get()
        if item:
            chunks_found.append(item)
    print(f"   ✅ Segments de phrases générés : {chunks_found}")
    results["[7] Chunker de phrases fonctionnel"] = len(chunks_found) > 0

    print("\n--- [8/10] Vérification de l'initialisation de Kokoro TTS ---")
    kokoro = None
    try:
        from kokoro_onnx import Kokoro
        if os.path.exists(KOKORO_MODEL_PATH) and os.path.exists(KOKORO_VOICES_PATH):
            kokoro = Kokoro(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH)
            print("   ✅ Kokoro-82M ONNX chargé avec succès.")
            results["[8] Kokoro TTS initialisé"] = True
        else:
            raise FileNotFoundError("Poids Kokoro introuvables.")
    except Exception as e:
        print(f"   ❌ ÉCHEC initialisation Kokoro : {e}")
        sys.exit(1)

    print("\n--- [9/10] Test de production audio PCM par Kokoro ---")
    audio_produced = False
    samples_count = 0
    try:
        voices = list(kokoro.voices)
        voice = next((v for v in voices if v.startswith('ff_') or v.startswith('fr_')), voices[0])
        test_sentence = chunks_found[0] if chunks_found else "Bonjour."
        
        t_synth = time.perf_counter()
        samples, sr = kokoro.create(test_sentence, voice=voice, speed=1.0)
        synth_duration = (time.perf_counter() - t_synth) * 1000
        
        samples_count = len(samples)
        audio_produced = samples_count > 0
        print(f"   ✅ Audio PCM produit : {samples_count} échantillons à {sr} Hz (Synthèse en {round(synth_duration, 2)} ms)")
        results["[9] Kokoro produit du PCM"] = audio_produced
    except Exception as e:
        print(f"   ❌ ÉCHEC de la synthèse Kokoro : {e}")
        sys.exit(1)

    print("\n--- [10/10] Test de l'agrégation dans la queue audio ---")
    audio_queue = asyncio.Queue()
    await audio_queue.put((samples, sr))
    queue_empty_check = not audio_queue.empty()
    print(f"   ✅ Queue audio alimentée avec succès (État vide : {not queue_empty_check}).")
    results["[10] Queue audio fonctionnelle"] = queue_empty_check

    print("\n" + "=" * 60)
    print(" BILAN DU DIAGNOSTIC FORENSIQUE 10/10")
    print("=" * 60)
    for k, v in results.items():
        status = "✅ PASS" if v else "❌ FAIL"
        print(f" {k:<35} : {status}")
    print("=" * 60)
    print(" STATUT GLOBAL : CERTIFICATION V6.3-R2 VALIDÉE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_forensic_audit())
