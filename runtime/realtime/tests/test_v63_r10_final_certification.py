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

# --- CONFIGURATION STRICTE CPU ---
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"

TARGET_MODEL = "qwen3:4b"
KOKORO_DIR = r"G:\AI\E-zzio\runtime\realtime\models\kokoro"
KOKORO_MODEL_PATH = os.path.join(KOKORO_DIR, "kokoro-v0_19.onnx")
KOKORO_VOICES_PATH = os.path.join(KOKORO_DIR, "voices.bin")

class ThinkingTagFilter:
    """Filtre d'état pour intercepter et supprimer les blocs <think>...</think> du stream."""
    def __init__(self):
        self.in_think_block = False
        self.buffer = ""

    def process_token(self, token: str) -> str:
        self.buffer += token
        output = ""
        
        while True:
            if not self.in_think_block:
                start_idx = self.buffer.find("<think>")
                if start_idx != -1:
                    output += self.buffer[:start_idx]
                    self.buffer = self.buffer[start_idx + len("<think>"):]
                    self.in_think_block = True
                else:
                    # Garder un petit buffer de sécurité pour éviter de couper une balise à cheval sur 2 tokens
                    safe_len = max(0, len(self.buffer) - len("<think>"))
                    output += self.buffer[:safe_len]
                    self.buffer = self.buffer[safe_len:]
                    break
            else:
                end_idx = self.buffer.find("</think>")
                if end_idx != -1:
                    self.buffer = self.buffer[end_idx + len("</think>"):]
                    self.in_think_block = False
                else:
                    # Tout est dans le bloc thinking, on purge le buffer sans émettre
                    self.buffer = ""
                    break
        return output

    def flush(self) -> str:
        if not self.in_think_block:
            res = self.buffer
            self.buffer = ""
            return res
        return ""

async def certifier_pipeline_10_10():
    print("=" * 60)
    print(" E-ZZIO V7 — CERTIFICATION R10 (10/10 FAIL-CLOSED)")
    print("=" * 60)

    # 1. Initialisation Kokoro (Fail-Closed)
    try:
        from kokoro_onnx import Kokoro
        kokoro = Kokoro(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH)
        print("   ✅ Kokoro-82M ONNX initialisé.")
    except Exception as e:
        print(f"❌ Échec critique initialisation Kokoro : {e}")
        sys.exit(1)

    # 2. Files d'attente asynchrones
    text_queue = asyncio.Queue(maxsize=100)
    sentence_queue = asyncio.Queue(maxsize=10)
    audio_queue = asyncio.Queue(maxsize=10)
    cancel_event = asyncio.Event()

    # 3. Workers
    async def llm_worker():
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": TARGET_MODEL,
            "prompt": "Dis bonjour en un mot.",
            "stream": True,
            "think": False,
            "options": {"num_predict": 256, "temperature": 0.1}
        }
        
        tag_filter = ThinkingTagFilter()
        clean_chars_emitted = 0

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"Ollama HTTP {resp.status}")

                    async for line in resp.content:
                        if cancel_event.is_set(): break
                        data = json.loads(line.decode('utf-8'))
                        raw_token = data.get("response") or data.get("message", {}).get("content", "")
                        
                        if raw_token:
                            filtered_text = tag_filter.process_token(raw_token)
                            if filtered_text:
                                clean_chars_emitted += len(filtered_text)
                                await text_queue.put(filtered_text)

                        if data.get("done", False):
                            break
            
            # Flush final du filtre
            final_text = tag_filter.flush()
            if final_text:
                clean_chars_emitted += len(final_text)
                await text_queue.put(final_text)

        except Exception as e:
            print(f"❌ Erreur worker LLM : {e}")
        finally:
            print(f"   ℹ️ Fin LLM Worker. Caractères utiles transmis : {clean_chars_emitted}")
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
                chunk = sentences[0].strip()
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
            
            print(f"   🔊 [TTS] Synthèse de la phrase : \"{sentence}\"")
            t0 = time.perf_counter()
            # Isolation thread pour ne pas bloquer l'event loop asyncio
            samples, sr = await asyncio.to_thread(kokoro.create, sentence, voice=v, speed=1.0)
            
            if len(samples) > 0:
                rtf = (time.perf_counter() - t0) / (len(samples) / sr)
                chunks_processed += 1
                await audio_queue.put((samples, rtf))

    # 4. Exécution concurrente
    print("[RUN] Démarrage du pipeline asynchrone...")
    t_start = time.perf_counter()
    tasks = [
        asyncio.create_task(llm_worker()),
        asyncio.create_task(chunker_worker()),
        asyncio.create_task(tts_worker())
    ]

    # Supervision Forensique avec Timeout Fail-Closed (15s max)
    results = {"audio_chunks": 0, "rtfs": []}
    try:
        while True:
            audio_item = await asyncio.wait_for(audio_queue.get(), timeout=15.0)
            if audio_item is None:
                break
            samples, rtf = audio_item
            results["audio_chunks"] += 1
            results["rtfs"].append(rtf)
    except asyncio.TimeoutError:
        print("❌ FAIL-CLOSED : Timeout (15s) de la file d'attente audio.")
        cancel_event.set()
        sys.exit(1)

    full_duration = time.perf_counter() - t_start

    # 5. Rapport Final & Certification
    print("\n" + "=" * 60)
    print(" BILAN DE CERTIFICATION V6.3-R10")
    print("=" * 60)
    print(f" • Segments Audio Générés : {results['audio_chunks']}")
    print(f" • RTF Moyen (Kokoro)     : {round(sum(results['rtfs'])/len(results['rtfs']), 3) if results['rtfs'] else 'N/A'}")
    print(f" • Durée totale pipeline  : {round(full_duration, 2)} s")
    print("=" * 60)

    # Règle de validation 10/10 stricte
    if results["audio_chunks"] > 0 and all(r < 1.5 for r in results['rtfs']):
        print("✨ CERTIFICATION V6.3-R10 : PASS (10/10 VALIDÉ)")
        print("=" * 60)
    else:
        print("❌ FAIL-CLOSED : Critères 10/10 non atteints.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(certifier_pipeline_10_10())
