import sys
import asyncio
import time
import os
import json
import re
import aiohttp

sys.path.insert(0, r'G:\AI\E-zzio')

os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"

TARGET_MODEL = "qwen3:4b"
KOKORO_MODEL_PATH = r"G:\AI\E-zzio\runtime\realtime\models\kokoro\kokoro-v0_19.onnx"
KOKORO_VOICES_PATH = r"G:\AI\E-zzio\runtime\realtime\models\kokoro\voices.bin"

from kokoro_onnx import Kokoro
kokoro = Kokoro(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH)

def get_voice():
    voices = list(kokoro.voices)
    fr_voice = next((v for v in voices if v.startswith("fr_") or v.startswith("ff_")), None)
    if fr_voice:
        return fr_voice, "FRANÇAISE"
    return voices[0], "FALLBACK (Non-FR)"

SELECTED_VOICE, VOICE_TYPE = get_voice()

class ContextualAdaptiveChunker:
    def __init__(self):
        self.buffer = ""
        self.chunk_count = 0

    def get_target_size(self) -> int:
        if self.chunk_count == 0:
            return 28  # Réactivité maximale premier chunk
        elif self.chunk_count < 4:
            return 40  # Standard conversationnel
        else:
            return 52  # Narration longue

    def feed(self, token: str):
        self.buffer += token
        chunks = []
        target = self.get_target_size()

        while True:
            match = re.search(r'([.!?,\n;:—]+)', self.buffer)
            if match:
                end_pos = match.end()
                candidate = self.buffer[:end_pos].strip()
                if len(candidate) >= 12 or len(self.buffer) >= target:
                    chunks.append(candidate)
                    self.buffer = self.buffer[end_pos:]
                    self.chunk_count += 1
                    target = self.get_target_size()
                else:
                    break
            else:
                if len(self.buffer) >= target:
                    space_pos = self.buffer.rfind(" ")
                    if space_pos >= 12:
                        chunks.append(self.buffer[:space_pos].strip())
                        self.buffer = self.buffer[space_pos:]
                        self.chunk_count += 1
                    else:
                        break
                else:
                    break
        return chunks

    def flush(self):
        remainder = self.buffer.strip()
        self.reset()
        if len(remainder) >= 2:
            return [remainder]
        return []

    def reset(self):
        self.buffer = ""
        self.chunk_count = 0

async def simulate_turn(session, turn_id, prompt):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": TARGET_MODEL,
        "prompt": prompt,
        "stream": True,
        "think": False,
        "options": {"num_predict": 64, "temperature": 0.5}
    }

    chunker = ContextualAdaptiveChunker()
    t0 = time.perf_counter()
    ttfa = 0.0
    audio_chunks = 0
    first_audio = False
    interrupted = False
    
    # Simulation d'un barge-in au tour 3 à mi-parcours
    barge_in_triggered = (turn_id == 3)
    cancel_event = asyncio.Event()

    try:
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                return {"status": f"HTTP {resp.status}"}

            async for line in resp.content:
                if cancel_event.is_set():
                    interrupted = True
                    break
                if not line: continue
                data = json.loads(line.decode('utf-8'))
                token = data.get("response") or data.get("message", {}).get("content", "")

                if token:
                    chunks = chunker.feed(token)
                    for c in chunks:
                        t_synth = time.perf_counter()
                        samples, sr = await asyncio.to_thread(kokoro.create, c, voice=SELECTED_VOICE, speed=1.0)
                        if len(samples) > 0:
                            audio_chunks += 1
                            if not first_audio:
                                ttfa = (time.perf_counter() - t0) * 1000
                                first_audio = True
                        
                        # Déclenchement du Barge-in simulé
                        if barge_in_triggered and audio_chunks >= 2:
                            cancel_event.set()

                if data.get("done") or interrupted: break

        return {
            "status": "INTERRUPTED (Barge-in)" if interrupted else "OK",
            "ttfa_ms": round(ttfa),
            "audio_chunks": audio_chunks
        }
    except Exception as e:
        return {"status": f"ERR: {str(e)[:15]}"}

async def run_r15():
    print("=" * 70)
    print(" E-ZZIO V7 — CERTIFICATION R15 (STABILITÉ & BARGE-IN)")
    print(f" Voix : {SELECTED_VOICE} [{VOICE_TYPE}] | Chunker : Adaptatif (28-52)")
    print("=" * 70)
    print(f"{'Tour':<6} | {'Prompt':<25} | {'TTFA (ms)':<10} | {'Chunks':<8} | {'Statut'}")
    print("-" * 70)

    prompts = [
        "Dis bonjour en une phrase.",
        "Pourquoi l'asynchronisme est clé ?",
        "Interromps-moi si tu peux.",  # Tour 3 : Test Barge-in
        "Quelle heure est-il ?",
        "Confirme la fin du test."
    ]

    async with aiohttp.ClientSession() as session:
        for i, p in enumerate(prompts, 1):
            res = await simulate_turn(session, i, p)
            print(f"T{i:<5} | {p[:24]:<25} | {str(res.get('ttfa','-')):<10} | {str(res.get('audio_chunks','-')):<8} | {res['status']}")
            await asyncio.sleep(0.5)

    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_r15())
