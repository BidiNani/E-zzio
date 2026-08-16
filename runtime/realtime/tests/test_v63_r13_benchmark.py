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

MODELS_TO_TEST = ["qwen3:4b", "gemma4e4b:latest", "gemma2:2b", "qwen2.5-coder:7b"]
KOKORO_MODEL_PATH = r"G:\AI\E-zzio\runtime\realtime\models\kokoro\kokoro-v0_19.onnx"
KOKORO_VOICES_PATH = r"G:\AI\E-zzio\runtime\realtime\models\kokoro\voices.bin"

from kokoro_onnx import Kokoro
kokoro = Kokoro(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH)

def get_best_voice(kokoro_inst):
    voices = list(kokoro_inst.voices)
    if not voices:
        raise RuntimeError("Fichier voices.bin vide ou corrompu.")
    fr_voice = next((v for v in voices if v.startswith("fr_") or v.startswith("ff_")), None)
    return fr_voice if fr_voice else voices[0]

SELECTED_VOICE = get_best_voice(kokoro)

class BoundedSentenceChunker:
    def __init__(self, min_chars=8, max_chars=100):
        self.buffer = ""
        self.min_chars = min_chars
        self.max_chars = max_chars

    def feed(self, token: str):
        self.buffer += token
        chunks = []
        while True:
            match = re.search(r'([.!?\n]+)', self.buffer)
            if match:
                end_pos = match.end()
                candidate = self.buffer[:end_pos].strip()
                if len(candidate) >= self.min_chars:
                    chunks.append(candidate)
                    self.buffer = self.buffer[end_pos:]
                elif len(self.buffer) > self.max_chars:
                    chunks.append(candidate)
                    self.buffer = self.buffer[end_pos:]
                else:
                    break
            else:
                if len(self.buffer) >= self.max_chars:
                    space_pos = self.buffer.rfind(" ")
                    if space_pos > self.min_chars:
                        chunks.append(self.buffer[:space_pos].strip())
                        self.buffer = self.buffer[space_pos:]
                    else:
                        chunks.append(self.buffer.strip())
                        self.buffer = ""
                break
        return chunks

    def flush(self):
        remainder = self.buffer.strip()
        self.buffer = ""
        if len(remainder) >= 2:
            return [remainder]
        return []

async def test_single_model(model_name):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model_name,
        "prompt": "Explique en deux phrases pourquoi la voix nécessite du streaming.",
        "stream": True,
        "think": False,
        "options": {"num_predict": 96, "temperature": 0.5}
    }

    stats = {
        "ttft_ms": 0.0,
        "ttfa_ms": 0.0,
        "think_chars": 0,
        "resp_chars": 0,
        "audio_chunks": 0,
        "rtfs": [],
        "status": "FAIL"
    }

    t0 = time.perf_counter()
    chunker = BoundedSentenceChunker(min_chars=8, max_chars=100)
    first_token_captured = False
    first_audio_captured = False

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 404:
                    stats["status"] = "404 NOT FOUND"
                    return stats
                elif resp.status != 200:
                    stats["status"] = f"HTTP {resp.status}"
                    return stats

                async for line in resp.content:
                    if not line: continue
                    data = json.loads(line.decode('utf-8'))
                    
                    think = data.get("thinking", "") or ""
                    token = data.get("response") or data.get("message", {}).get("content", "")
                    
                    if (think or token) and not first_token_captured:
                        stats["ttft_ms"] = (time.perf_counter() - t0) * 1000
                        first_token_captured = True

                    stats["think_chars"] += len(think)
                    stats["resp_chars"] += len(token)

                    if token:
                        sentences = chunker.feed(token)
                        for s in sentences:
                            t_synth = time.perf_counter()
                            samples, sr = await asyncio.to_thread(kokoro.create, s, voice=SELECTED_VOICE, speed=1.0)
                            
                            if len(samples) > 0:
                                synth_dur = time.perf_counter() - t_synth
                                audio_dur = len(samples) / sr
                                stats["rtfs"].append(synth_dur / audio_dur)
                                stats["audio_chunks"] += 1

                                if not first_audio_captured:
                                    stats["ttfa_ms"] = (time.perf_counter() - t0) * 1000
                                    first_audio_captured = True

                    if data.get("done"): break

                final_sentences = chunker.flush()
                for s in final_sentences:
                    t_synth = time.perf_counter()
                    samples, sr = await asyncio.to_thread(kokoro.create, s, voice=SELECTED_VOICE, speed=1.0)
                    if len(samples) > 0:
                        synth_dur = time.perf_counter() - t_synth
                        audio_dur = len(samples) / sr
                        stats["rtfs"].append(synth_dur / audio_dur)
                        stats["audio_chunks"] += 1
                        if not first_audio_captured:
                            stats["ttfa_ms"] = (time.perf_counter() - t0) * 1000
                            first_audio_captured = True

        stats["status"] = "OK" if stats["audio_chunks"] > 0 else "NO AUDIO"
        return stats

    except Exception as e:
        stats["status"] = f"ERR: {str(e)[:20]}"
        return stats

async def run_benchmark():
    print("=" * 70)
    print(" E-ZZIO V7 — BENCHMARK FORENSIQUE V6.3-R13")
    print(f" Voix Kokoro sélectionnée : {SELECTED_VOICE}")
    print("=" * 70)
    print(f"{'Modèle':<20} | {'TTFT (ms)':<10} | {'TTFA (ms)':<10} | {'Thinking':<8} | {'RTF Moy':<8} | {'Statut'}")
    print("-" * 70)

    for model in MODELS_TO_TEST:
        res = await test_single_model(model)
        if res["status"] == "OK":
            avg_rtf = round(sum(res["rtfs"]) / len(res["rtfs"]), 3) if res["rtfs"] else 0.0
            print(f"{model:<20} | {round(res['ttft_ms']):<10} | {round(res['ttfa_ms']):<10} | {res['think_chars']:<8} | {avg_rtf:<8} | PASS")
        else:
            print(f"{model:<20} | {'-':<10} | {'-':<10} | {res['think_chars']:<8} | {'-':<8} | {res['status']}")

    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
