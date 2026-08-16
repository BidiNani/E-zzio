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
CHUNK_THRESHOLDS = [16, 32, 48, 64]
KOKORO_MODEL_PATH = r"G:\AI\E-zzio\runtime\realtime\models\kokoro\kokoro-v0_19.onnx"
KOKORO_VOICES_PATH = r"G:\AI\E-zzio\runtime\realtime\models\kokoro\voices.bin"

from kokoro_onnx import Kokoro
kokoro = Kokoro(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH)

def get_best_voice(kokoro_inst):
    voices = list(kokoro_inst.voices)
    if not voices:
        raise RuntimeError("Fichier voices.bin vide.")
    fr_voice = next((v for v in voices if v.startswith("fr_") or v.startswith("ff_")), None)
    return fr_voice if fr_voice else voices[0]

SELECTED_VOICE = get_best_voice(kokoro)

class AdaptiveStreamChunker:
    def __init__(self, target_chars: int):
        self.buffer = ""
        self.target_chars = target_chars

    def feed(self, token: str):
        self.buffer += token
        chunks = []
        
        while True:
            # Recherche prioritaire de ponctuation (principale ou secondaire)
            match = re.search(r'([.!?,\n;:—]+)', self.buffer)
            if match:
                end_pos = match.end()
                candidate = self.buffer[:end_pos].strip()
                if len(candidate) >= 8:
                    chunks.append(candidate)
                    self.buffer = self.buffer[end_pos:]
                elif len(self.buffer) >= self.target_chars:
                    chunks.append(candidate)
                    self.buffer = self.buffer[end_pos:]
                else:
                    break
            else:
                # Si pas de ponctuation mais seuil dépassé, couper au dernier espace
                if len(self.buffer) >= self.target_chars:
                    space_pos = self.buffer.rfind(" ")
                    if space_pos >= 8:
                        chunks.append(self.buffer[:space_pos].strip())
                        self.buffer = self.buffer[space_pos:]
                    else:
                        break
                else:
                    break
        return chunks

    def flush(self):
        remainder = self.buffer.strip()
        self.buffer = ""
        if len(remainder) >= 2:
            return [remainder]
        return []

async def benchmark_threshold(threshold):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": TARGET_MODEL,
        "prompt": "Explique pourquoi le streaming vocal par petits morceaux réduit la latence pour l'utilisateur.",
        "stream": True,
        "think": False,
        "options": {"num_predict": 128, "temperature": 0.5}
    }

    t0 = time.perf_counter()
    chunker = AdaptiveStreamChunker(target_chars=threshold)
    
    stats = {
        "threshold": threshold,
        "ttft_ms": 0.0,
        "ttfa_ms": 0.0,
        "audio_chunks": 0,
        "rtfs": [],
        "total_audio_sec": 0.0
    }

    first_token_captured = False
    first_audio_captured = False

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    return None

                async for line in resp.content:
                    if not line: continue
                    data = json.loads(line.decode('utf-8'))
                    
                    token = data.get("response") or data.get("message", {}).get("content", "")
                    
                    if token and not first_token_captured:
                        stats["ttft_ms"] = (time.perf_counter() - t0) * 1000
                        first_token_captured = True

                    if token:
                        chunks = chunker.feed(token)
                        for chunk_text in chunks:
                            t_synth = time.perf_counter()
                            samples, sr = await asyncio.to_thread(kokoro.create, chunk_text, voice=SELECTED_VOICE, speed=1.0)
                            
                            if len(samples) > 0:
                                synth_dur = time.perf_counter() - t_synth
                                audio_dur = len(samples) / sr
                                stats["rtfs"].append(synth_dur / audio_dur)
                                stats["total_audio_sec"] += audio_dur
                                stats["audio_chunks"] += 1

                                if not first_audio_captured:
                                    stats["ttfa_ms"] = (time.perf_counter() - t0) * 1000
                                    first_audio_captured = True

                    if data.get("done"): break

                # Vidange finale
                for chunk_text in chunker.flush():
                    t_synth = time.perf_counter()
                    samples, sr = await asyncio.to_thread(kokoro.create, chunk_text, voice=SELECTED_VOICE, speed=1.0)
                    if len(samples) > 0:
                        synth_dur = time.perf_counter() - t_synth
                        audio_dur = len(samples) / sr
                        stats["rtfs"].append(synth_dur / audio_dur)
                        stats["total_audio_sec"] += audio_dur
                        stats["audio_chunks"] += 1
                        if not first_audio_captured:
                            stats["ttfa_ms"] = (time.perf_counter() - t0) * 1000
                            first_audio_captured = True

        return stats

    except Exception as e:
        print(f"❌ Erreur seuil {threshold}: {e}")
        return None

async def run_suite():
    print("=" * 70)
    print(" E-ZZIO V7 — BENCHMARK V6.3-R14 (CHUNK SIZE OPTIMIZATION)")
    print(f" Modèle : {TARGET_MODEL} | Voix : {SELECTED_VOICE}")
    print("=" * 70)
    print(f"{'Seuil Chunker':<15} | {'TTFT (ms)':<10} | {'TTFA (ms)':<10} | {'Delta TTFA-TTFT':<15} | {'Chunks Audio':<12} | {'RTF Moy'}")
    print("-" * 70)

    for th in CHUNK_THRESHOLDS:
        res = await benchmark_threshold(th)
        if res:
            delta = round(res['ttfa_ms'] - res['ttft_ms']) if res['ttfa_ms'] > 0 else 0
            avg_rtf = round(sum(res['rtfs']) / len(res['rtfs']), 3) if res['rtfs'] else 0.0
            print(f"{th:<15} | {round(res['ttft_ms']):<10} | {round(res['ttfa_ms']):<10} | {delta:<15} | {res['audio_chunks']:<12} | {avg_rtf}")
        else:
            print(f"{th:<15} | FAIL")

    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_suite())
