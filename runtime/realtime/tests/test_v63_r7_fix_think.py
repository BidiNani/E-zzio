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
print(" E-ZZIO V7 — QUALIFICATION V6.3-R7 (FIX THINKING & PIPELINE)")
print("=" * 60)

TARGET_MODEL = "qwen3:4b"
KOKORO_DIR = r"G:\AI\E-zzio\runtime\realtime\models\kokoro"
KOKORO_MODEL_PATH = os.path.join(KOKORO_DIR, "kokoro-v0_19.onnx")
KOKORO_VOICES_PATH = os.path.join(KOKORO_DIR, "voices.bin")

async def test_r7_pipeline():
    url = "http://localhost:11434/api/generate"
    # Correction : "think": False positionné à la racine du payload de l'API Ollama
    payload = {
        "model": TARGET_MODEL,
        "prompt": "Réponds en un seul mot : Bonjour.",
        "stream": True,
        "think": False, 
        "options": {"num_predict": 48, "temperature": 0.1}
    }

    text_queue = asyncio.Queue()
    sentence_queue = asyncio.Queue()
    audio_queue = asyncio.Queue()
    cancel_event = asyncio.Event()

    print("[RUN] Test du streaming Ollama avec 'think': False à la racine...")

    async def llm_worker():
        token_received = 0
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        text_err = await resp.text()
                        print(f"❌ Erreur HTTP Ollama : {text_err}")
                        await text_queue.put(None)
                        return

                    async for line in resp.content:
                        if cancel_event.is_set():
                            break
                        if line:
                            data = json.loads(line.decode('utf-8'))
                            # On récupère le texte, en vérifiant si le modèle répond dans response ou message
                            token = data.get("response") or data.get("message", {}).get("content", "")
                            if token:
                                token_received += 1
                                await text_queue.put(token)
                            if data.get("done", False):
                                break
        except Exception as e:
            print(f"❌ Exception LLM Worker : {e}")
        finally:
            print(f"   ℹ️ Fin du worker LLM. Total tokens response reçus : {token_received}")
            await text_queue.put(None)

    async def chunker_worker():
        buffer = ""
        while not cancel_event.is_set():
            token = await text_queue.get()
            if token is None:
                if buffer.strip():
                    await sentence_queue.put(buffer.strip())
                await sentence_queue.put(None)
                break
            buffer += token
            sentences = re.split(r'([.!?\n])', buffer)
            if len(sentences) > 1:
                await sentence_queue.put(sentences[0].strip())
                buffer = "".join(sentences[1:])

    async def tts_worker(kokoro):
        voices = list(kokoro.voices)
        v = next((v for v in voices if v.startswith('ff_') or v.startswith('fr_')), voices[0])
        chunks_count = 0
        while not cancel_event.is_set():
            sentence = await sentence_queue.get()
            if sentence is None:
                await audio_queue.put(None)
                break
            
            print(f"   🔊 [TTS Synthèse] Phrase reçue : \"{sentence}\"")
            t0 = time.perf_counter()
            samples, sr = kokoro.create(sentence, voice=v, speed=1.0)
            rtf = (time.perf_counter() - t0) / (len(samples)/sr) if len(samples) > 0 else 0.0
            chunks_count += 1
            await audio_queue.put((samples, rtf))
        print(f"   ℹ️ Fin TTS Worker. Chunks audio générés : {chunks_count}")

    # Initialisation de Kokoro
    try:
        from kokoro_onnx import Kokoro
        kokoro = Kokoro(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH)
        print("   ✅ Kokoro initialisé.")
    except Exception as e:
        print(f"❌ Erreur initialisation Kokoro : {e}")
        sys.exit(1)

    t_start = time.perf_counter()
    tasks = [
        asyncio.create_task(llm_worker()),
        asyncio.create_task(chunker_worker()),
        asyncio.create_task(tts_worker(kokoro))
    ]

    # Supervision de l'audio queue avec timeout de sécurité de 10 secondes
    audio_chunks = 0
    rtfs = []
    try:
        while True:
            audio_item = await asyncio.wait_for(audio_queue.get(), timeout=10.0)
            if audio_item is None:
                break
            samples, rtf = audio_item
            audio_chunks += 1
            rtfs.append(rtf)
    except asyncio.TimeoutError:
        print("❌ FAIL : Timeout (10s) de la file d'attente audio. Le pipeline est bloqué.")
        cancel_event.set()
        sys.exit(1)

    full_time = time.perf_counter() - t_start
    print("\n" + "=" * 60)
    print(" RÉSULTATS CERTIFICATION V6.3-R7")
    print("=" * 60)
    print(f" • Chunks audio produits : {audio_chunks}")
    print(f" • RTF moyen (Kokoro)    : {round(sum(rtfs)/len(rtfs), 3) if rtfs else 'N/A'}")
    print(f" • Temps total d'exécution : {round(full_time, 2)}s")
    print("=" * 60)

    if audio_chunks > 0:
        print("✨ CERTIFICATION V6.3-R7 : PASS (10/10)")
    else:
        print("❌ FAIL : Aucun audio généré.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_r7_pipeline())
