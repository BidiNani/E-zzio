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

# --- CONFIGURATION STRICTE ---
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"

TARGET_MODEL = "qwen3:4b"
KOKORO_DIR = r"G:\AI\E-zzio\runtime\realtime\models\kokoro"
KOKORO_MODEL_PATH = os.path.join(KOKORO_DIR, "kokoro-v0_19.onnx")
KOKORO_VOICES_PATH = os.path.join(KOKORO_DIR, "voices.bin")

async def certifier_pipeline():
    print("=" * 60)
    print(" E-ZZIO V7 — CERTIFICATION R5 (CONCURRENCE & STREAMING)")
    print("=" * 60)

    # 1. Vérification Ollama
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:11434/api/tags", timeout=3.0) as resp:
                data = await resp.json()
                if not any(TARGET_MODEL in m["name"] for m in data["models"]):
                    raise RuntimeError(f"Modèle {TARGET_MODEL} absent.")
    except Exception as e:
        print(f"❌ FAIL: Ollama/Modèle non prêt : {e}"); sys.exit(1)

    # 2. Files d'attente (Queues bornées pour éviter le memory leak)
    text_queue = asyncio.Queue(maxsize=100)
    sentence_queue = asyncio.Queue(maxsize=10)
    audio_queue = asyncio.Queue(maxsize=10)
    cancel_event = asyncio.Event()

    # 3. Workers
    async def llm_worker():
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": TARGET_MODEL,
            "prompt": "Explique brièvement pourquoi le streaming est vital pour le vocal.",
            "stream": True,
            "options": {"num_predict": 128, "temperature": 0.7, "think": False} # <--- Cible du fix
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    async for line in resp.content:
                        if cancel_event.is_set(): break
                        data = json.loads(line.decode('utf-8'))
                        # Parser robuste : réponse ou message.content
                        token = data.get("response") or data.get("message", {}).get("content", "")
                        if token: await text_queue.put(token)
                        if data.get("done"): break
        finally: await text_queue.put(None)

    async def chunker_worker():
        buffer = ""
        while not cancel_event.is_set():
            token = await text_queue.get()
            if token is None: 
                if buffer.strip(): await sentence_queue.put(buffer.strip())
                await sentence_queue.put(None); break
            buffer += token
            sentences = re.split(r'([.!?\n])', buffer)
            if len(sentences) > 1:
                await sentence_queue.put(sentences[0].strip())
                buffer = "".join(sentences[1:])

    async def tts_worker(kokoro):
        voices = list(kokoro.voices)
        v = next((v for v in voices if v.startswith('ff_') or v.startswith('fr_')), voices[0])
        while not cancel_event.is_set():
            sentence = await sentence_queue.get()
            if sentence is None: await audio_queue.put(None); break
            
            t0 = time.perf_counter()
            samples, sr = kokoro.create(sentence, voice=v, speed=1.0)
            rtf = (time.perf_counter() - t0) / (len(samples)/sr)
            await audio_queue.put((samples, rtf))

    # Initialisation Kokoro
    from kokoro_onnx import Kokoro
    kokoro = Kokoro(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH)

    # 4. Exécution concurrente
    print("[RUN] Démarrage du pipeline...")
    t_start = time.perf_counter()
    tasks = [
        asyncio.create_task(llm_worker()),
        asyncio.create_task(chunker_worker()),
        asyncio.create_task(tts_worker(kokoro))
    ]

    # Supervision du flux
    results = {"tokens": 0, "audio_chunks": 0, "rtfs": []}
    
    while True:
        try:
            audio_data = await asyncio.wait_for(audio_queue.get(), timeout=5.0)
            if audio_data is None: break
            results["audio_chunks"] += 1
            results["rtfs"].append(audio_data[1])
        except asyncio.TimeoutError:
            print("❌ FAIL: Pipeline bloqué (timeout)"); sys.exit(1)

    # 5. Certification Finale
    full_duration = time.perf_counter() - t_start
    print("\n" + "=" * 60)
    print(" BILAN DE CERTIFICATION V6.3-R5")
    print(f" • Chunks audio produits : {results['audio_chunks']}")
    print(f" • RTF moyen (Kokoro)    : {round(sum(results['rtfs'])/len(results['rtfs']), 3) if results['rtfs'] else 'N/A'}")
    print(f" • Temps total pipeline  : {round(full_duration, 2)}s")
    print("=" * 60)

    if results["audio_chunks"] > 0:
        print("✨ CERTIFICATION V6.3-R5 : PASS (10/10)")
    else:
        print("❌ FAIL: Pipeline n'a produit aucun audio.")
        sys.exit(1)

asyncio.run(certifier_pipeline())
