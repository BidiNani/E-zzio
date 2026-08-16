import sys
import asyncio
import time
import os
import json
import re
import aiohttp
from pathlib import Path

sys.path.insert(0, r'G:\AI\E-zzio')

# --- CONFIGURATION STRICTE CPU ---
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"

TARGET_MODEL = "qwen3:4b"
KOKORO_DIR = r"G:\AI\E-zzio\runtime\realtime\models\kokoro"
KOKORO_MODEL_PATH = os.path.join(KOKORO_DIR, "kokoro-v0_19.onnx")
KOKORO_VOICES_PATH = os.path.join(KOKORO_DIR, "voices.bin")

async def certifier_pipeline_r11():
    print("=" * 60)
    print(" E-ZZIO V7 — CERTIFICATION R11 (PIPELINE COMPLET 10/10)")
    print("=" * 60)

    # 1. Initialisation Kokoro (Fail-Closed)
    try:
        from kokoro_onnx import Kokoro
        kokoro = Kokoro(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH)
        print("   ✅ Kokoro-82M ONNX chargé avec succès.")
    except Exception as e:
        print(f"❌ Échec critique initialisation Kokoro : {e}")
        sys.exit(1)

    # 2. Files d'attente asynchrones
    text_queue = asyncio.Queue(maxsize=100)
    sentence_queue = asyncio.Queue(maxsize=10)
    audio_queue = asyncio.Queue(maxsize=10)
    cancel_event = asyncio.Event()

    # 3. Workers du Pipeline
    async def llm_worker():
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": TARGET_MODEL,
            "prompt": "Explique en deux phrases pourquoi une architecture asynchrone est indispensable pour la voix.",
            "stream": True,
            "think": False, # <--- La clé validée par le benchmark A/B/C
            "options": {"num_predict": 128, "temperature": 0.5}
        }
        
        tokens_emitted = 0
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"Ollama HTTP {resp.status}")

                    async for line in resp.content:
                        if cancel_event.is_set(): break
                        data = json.loads(line.decode('utf-8'))
                        token = data.get("response") or data.get("message", {}).get("content", "")
                        
                        if token:
                            tokens_emitted += 1
                            await text_queue.put(token)

                        if data.get("done", False):
                            break
        except Exception as e:
            print(f"❌ Erreur worker LLM : {e}")
        finally:
            print(f"   ℹ️ Fin LLM Worker. Tokens response transmis : {tokens_emitted}")
            await text_queue.put(None)

    async def chunker_worker():
        buffer = ""
        while not cancel_event.is_set():
            token = await text_queue.get()
            if token is None:
                cleaned = buffer.strip()
                if cleaned:
                    await sentence_queue.put(cleaned)
                await sentence_queue.put(None)
                break
            
            buffer += token
            sentences = re.split(r'([.!?\n])', buffer)
            if len(sentences) > 1:
                chunk = sentences[0].strip()
                # Règle absolue : interdiction stricte d'envoyer du vide à Kokoro
                if chunk:
                    await sentence_queue.put(chunk)
                buffer = "".join(sentences[1:])

    async def tts_worker():
        voices = list(kokoro.voices)
        v = next((v for v in voices if v.startswith('ff_') or v.startswith('fr_')), voices[0])
        chunks_processed = 0

        while not cancel_event.is_set():
            sentence = await sentence_queue.get()
            if sentence is None:
                await audio_queue.put(None)
                break
            
            # Sécurité supplémentaire anti-chaîne vide
            safe_sentence = sentence.strip()
            if not safe_sentence:
                continue
            
            print(f"   🔊 [TTS] Synthèse : \"{safe_sentence}\"")
            t0 = time.perf_counter()
            # Isolation thread pour protéger la boucle asyncio
            samples, sr = await asyncio.to_thread(kokoro.create, safe_sentence, voice=v, speed=1.0)
            
            if len(samples) > 0:
                rtf = (time.perf_counter() - t0) / (len(samples) / sr)
                chunks_processed += 1
                await audio_queue.put((samples, rtf))

    # 4. Exécution concurrente
    print("[RUN] Démarrage du pipeline asynchrone R11...")
    t_start = time.perf_counter()
    tasks = [
        asyncio.create_task(llm_worker()),
        asyncio.create_task(chunker_worker()),
        asyncio.create_task(tts_worker())
    ]

    # Supervision avec Timeout Fail-Closed (20s max)
    results = {"audio_chunks": 0, "rtfs": []}
    try:
        while True:
            audio_item = await asyncio.wait_for(audio_queue.get(), timeout=20.0)
            if audio_item is None:
                break
            samples, rtf = audio_item
            results["audio_chunks"] += 1
            results["rtfs"].append(rtf)
    except asyncio.TimeoutError:
        print("❌ FAIL-CLOSED : Timeout (20s) de la file d'attente audio.")
        cancel_event.set()
        sys.exit(1)

    full_duration = time.perf_counter() - t_start

    # 5. Rapport Final & Certification
    print("\n" + "=" * 60)
    print(" BILAN DE CERTIFICATION V6.3-R11")
    print("=" * 60)
    print(f" • Segments Audio Générés : {results['audio_chunks']}")
    print(f" • RTF Moyen (Kokoro)     : {round(sum(results['rtfs'])/len(results['rtfs']), 3) if results['rtfs'] else 'N/A'}")
    print(f" • Durée totale pipeline  : {round(full_duration, 2)} s")
    print("=" * 60)

    if results["audio_chunks"] > 0 and all(r < 1.5 for r in results['rtfs']):
        print("✨ CERTIFICATION V6.3-R11 : PASS (10/10 VALIDÉ)")
        print("=" * 60)
    else:
        print("❌ FAIL-CLOSED : Critères 10/10 non atteints.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(certifier_pipeline_r11())
