import sys
import asyncio
import time
import os
import json
import re
import aiohttp
import numpy as np
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, r'G:\AI\E-zzio')

# --- CONFIGURATION STRICTE ---
os.environ["OMP_NUM_THREADS"] = "2" # Réduction pour laisser place au LLM
os.environ["MKL_NUM_THREADS"] = "2"

TARGET_MODEL = "qwen3:4b"
KOKORO_DIR = r"G:\AI\E-zzio\runtime\realtime\models\kokoro"
KOKORO_MODEL_PATH = os.path.join(KOKORO_DIR, "kokoro-v0_19.onnx")
KOKORO_VOICES_PATH = os.path.join(KOKORO_DIR, "voices.bin")

async def certifier_pipeline():
    print("=" * 60)
    print(" E-ZZIO V7 — CERTIFICATION R8 (PIPELINE FORENSIQUE 10/10)")
    print("=" * 60)

    # 1. Init
    from kokoro_onnx import Kokoro
    kokoro = Kokoro(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH)
    
    # 2. Queues
    text_queue = asyncio.Queue(maxsize=100)
    sentence_queue = asyncio.Queue(maxsize=10)
    audio_queue = asyncio.Queue(maxsize=10)
    cancel_event = asyncio.Event()

    # 3. Workers
    async def llm_worker():
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": TARGET_MODEL,
            "prompt": "Réponds en une seule phrase : Le streaming est indispensable pour la voix.",
            "stream": True,
            "options": {"num_predict": 64, "temperature": 0.5, "think": False}
        }
        resp_found = False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    async for line in resp.content:
                        if cancel_event.is_set(): break
                        data = json.loads(line.decode('utf-8'))
                        
                        # Forensic : Séparation Thinking / Response
                        think = data.get("thinking", "")
                        resp_token = data.get("response") or data.get("message", {}).get("content", "")
                        
                        if resp_token:
                            resp_found = True
                            await text_queue.put(resp_token)
                        if data.get("done"): break
        finally:
            await text_queue.put(None)
            if not resp_found:
                print("❌ FAIL: Aucune donnée 'response' extraite du LLM.")

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
                chunk = sentences[0].strip()
                if chunk: await sentence_queue.put(chunk)
                buffer = "".join(sentences[1:])

    async def tts_worker():
        voices = list(kokoro.voices)
        v = next((v for v in voices if v.startswith('ff_') or v.startswith('fr_')), voices[0])
        while not cancel_event.is_set():
            sentence = await sentence_queue.get()
            if sentence is None: await audio_queue.put(None); break
            
            # Isolation de Kokoro via thread (ne bloque pas l'event loop)
            t0 = time.perf_counter()
            samples, sr = await asyncio.to_thread(kokoro.create, sentence, voice=v, speed=1.0)
            
            if len(samples) > 0:
                rtf = (time.perf_counter() - t0) / (len(samples)/sr)
                await audio_queue.put((samples, rtf))

    # 4. Exécution
    print("[RUN] Pipeline lancé...")
    t_start = time.perf_counter()
    tasks = [asyncio.create_task(w) for w in [llm_worker(), chunker_worker(), tts_worker()]]

    # Supervision Forensique
    results = {"audio_chunks": 0, "rtfs": []}
    while True:
        try:
            audio_data = await asyncio.wait_for(audio_queue.get(), timeout=5.0)
            if audio_data is None: break
            results["audio_chunks"] += 1
            results["rtfs"].append(audio_data[1])
        except asyncio.TimeoutError:
            print("❌ FAIL: Pipeline bloqué (timeout)"); sys.exit(1)

    # 5. Certification
    full_duration = time.perf_counter() - t_start
    print("\n" + "=" * 60)
    print(" BILAN CERTIFICATION 10/10")
    print(f" • Segments Audio : {results['audio_chunks']}")
    print(f" • RTF Moyen      : {round(sum(results['rtfs'])/len(results['rtfs']), 3) if results['rtfs'] else 'N/A'}")
    print("=" * 60)

    if results["audio_chunks"] > 0 and all(r < 1.5 for r in results['rtfs']):
        print("✨ CERTIFICATION R8 : PASS (10/10)")
    else:
        print("❌ FAIL: RTF trop élevé ou aucun audio.")
        sys.exit(1)

asyncio.run(certifier_pipeline())
