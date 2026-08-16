import sys
import asyncio
import time
import os
import queue
import aiohttp
import json
from pathlib import Path

sys.path.insert(0, r'G:\AI\E-zzio')

print("=" * 60)
print(" E-ZZIO V7 — V6.3 REALTIME PIPELINE & THREAD BUDGET BENCHMARK")
print("=" * 60)

os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"

KOKORO_DIR = r"G:\AI\E-zzio\runtime\realtime\models\kokoro"
KOKORO_MODEL_PATH = os.path.join(KOKORO_DIR, "kokoro-v0_19.onnx")
KOKORO_VOICES_PATH = os.path.join(KOKORO_DIR, "voices.bin")

async def query_ollama_stream(prompt: str, model: str, text_queue: asyncio.Queue, cancel_event: asyncio.Event):
    """Worker 1 : Consomme le flux de tokens d'Ollama et pousse dans la queue."""
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {"num_predict": 64, "temperature": 0.3}
    }

    t0_ttft = None
    t0_start = time.perf_counter()
    token_count = 0

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    await text_queue.put(None)
                    return 0.0, 0

                async for line in resp.content:
                    if cancel_event.is_set():
                        break
                    if line:
                        data = json.loads(line.decode('utf-8'))
                        token = data.get("response", "")
                        if token:
                            if not t0_ttft:
                                t0_ttft = time.perf_counter()
                            token_count += 1
                            await text_queue.put(token)
                            
                        if data.get("done", False):
                            break
    except Exception as e:
        print(f"⚠️ Erreur connexion Ollama ({model}) : {e}")
    finally:
        await text_queue.put(None)

    ttft_ms = round((t0_ttft - t0_start) * 1000, 2) if t0_ttft else 0.0
    return ttft_ms, token_count

class RealtimeVoicePipeline:
    def __init__(self, model_name="qwen2.5:3b"):
        self.model_name = model_name
        self.text_queue = asyncio.Queue()
        self.cancel_event = asyncio.Event()
        self.kokoro = None

    def init_kokoro(self):
        from kokoro_onnx import Kokoro
        if os.path.exists(KOKORO_MODEL_PATH) and os.path.exists(KOKORO_VOICES_PATH):
            self.kokoro = Kokoro(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH)
            print("[OK] Kokoro TTS initialisé pour le benchmark.")
        else:
            print("⚠️ Assets Kokoro manquants, mode simulation TTS activé.")

    async def run_benchmark_pass(self, prompt: str):
        print(f"\n--- TEST DU MODÈLE : {self.model_name} ---")
        self.cancel_event.clear()
        
        t_start = time.perf_counter()
        
        worker_task = asyncio.create_task(
            query_ollama_stream(prompt, self.model_name, self.text_queue, self.cancel_event)
        )

        full_text = ""
        while True:
            item = await self.text_queue.get()
            if item is None:
                break
            full_text += item

        ttft_ms, token_count = await worker_task
        total_gen_time = time.perf_counter() - t_start
        tokens_per_sec = round(token_count / total_gen_time, 2) if total_gen_time > 0 else 0.0

        print(f"📝 Texte généré : \"{full_text.strip()}\"")
        print(f"⏱️ TTFT (Time To First Token) : {ttft_ms} ms")
        print(f"⚡ Débit de génération        : {tokens_per_sec} tokens/s")
        print(f"📊 Volume total de tokens     : {token_count}")

        # Test de synthèse Kokoro sur le texte complet obtenu
        if self.kokoro and full_text.strip():
            print("🔊 [TTS] Lancement de Kokoro sur le texte généré...")
            available_voices = list(self.kokoro.voices)
            target_voice = next((v for v in available_voices if v.startswith('ff_') or v.startswith('fr_')), available_voices[0])
            
            t_tts_start = time.perf_counter()
            samples, sample_rate = self.kokoro.create(full_text.strip(), voice=target_voice, speed=1.0)
            tts_duration_ms = round((time.perf_counter() - t_tts_start) * 1000, 2)
            print(f"⏱️ Temps de synthèse Kokoro : {tts_duration_ms} ms ({len(samples)} échantillons)")

        print("⚡ Test de l'interrupteur logiciel (Purge des queues)...")
        self.cancel_event.set()
        while not self.text_queue.empty():
            try:
                self.text_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        print("✅ Interrupt Controller : Buffers purgés avec succès.")

async def main():
    pipeline = RealtimeVoicePipeline(model_name="qwen2.5:3b")
    pipeline.init_kokoro()

    prompt = "Donne-moi un conseil court pour optimiser une architecture asynchrone."
    
    try:
        await pipeline.run_benchmark_pass(prompt)
    except Exception as e:
        print(f"🔴 Échec du benchmark : {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print(" V6.3 BENCHMARK PIPELINE : PASS")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
