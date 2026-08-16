import sys
import asyncio
import time
import os
import json
import re
import aiohttp
from pathlib import Path

sys.path.insert(0, r'G:\AI\E-zzio')

# --- CONFIG ---
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"

MODELS = ["qwen3:4b", "gemma4e4b:latest", "gemma2:2b", "qwen2.5-coder:7b"]
KOKORO_MODEL_PATH = r"G:\AI\E-zzio\runtime\realtime\models\kokoro\kokoro-v0_19.onnx"
KOKORO_VOICES_PATH = r"G:\AI\E-zzio\runtime\realtime\models\kokoro\voices.bin"

from kokoro_onnx import Kokoro
kokoro = Kokoro(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH)

def chunker(buffer):
    # Regex garde la ponctuation collée à la phrase
    pattern = r'([^.!?\n]*[.!?\n])'
    sentences = re.findall(pattern, buffer)
    remainder = re.sub(pattern, '', buffer)
    return sentences, remainder

async def benchmark_model(model):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": "Explique pourquoi le streaming est vital pour le vocal en une phrase.",
        "stream": True,
        "think": False,
        "options": {"num_predict": 64, "temperature": 0.5}
    }

    t0 = time.perf_counter()
    stats = {"ttft": 0.0, "ttfa": 0.0, "think_chars": 0, "resp_chars": 0, "audio_chunks": 0, "rtfs": []}
    
    thinking_buffer = ""
    response_buffer = ""
    first_audio_captured = False
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200: return None
                
                async for line in resp.content:
                    if not line: continue
                    data = json.loads(line.decode('utf-8'))
                    
                    # Capture brute
                    think = data.get("thinking", "") or ""
                    resp_t = data.get("response") or data.get("message", {}).get("content", "")
                    
                    if (think or resp_t) and stats["ttft"] == 0:
                        stats["ttft"] = (time.perf_counter() - t0) * 1000
                    
                    thinking_buffer += think
                    response_buffer += resp_t
                    
                    # Chunker simple pour mesurer TTFA (Time To First Audio)
                    sentences, _ = chunker(response_buffer)
                    if sentences and not first_audio_captured:
                        t_tts = time.perf_counter()
                        s, sr = kokoro.create(sentences[0], voice="ff_siwis", speed=1.0)
                        stats["ttfa"] = (time.perf_counter() - t0) * 1000
                        stats["rtfs"].append((time.perf_counter() - t_tts) / (len(s)/sr))
                        stats["audio_chunks"] += 1
                        first_audio_captured = True
                        
                    if data.get("done"): break
                    
        stats["think_chars"] = len(thinking_buffer)
        stats["resp_chars"] = len(response_buffer)
        return stats
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return None

async def main():
    print("=" * 60)
    print(" E-ZZIO V7 — BENCHMARK FORENSIQUE A/B/C")
    print("=" * 60)
    print(f"{'Modèle':<18} | {'TTFT':<7} | {'TTFA':<7} | {'Think':<6} | {'Resp':<6} | {'RTF':<5}")
    print("-" * 65)
    
    for m in MODELS:
        res = await benchmark_model(m)
        if res:
            avg_rtf = round(sum(res['rtfs'])/len(res['rtfs']), 3) if res['rtfs'] else 0
            print(f"{m:<18} | {round(res['ttft']):<7} | {round(res['ttfa']):<7} | {res['think_chars']:<6} | {res['resp_chars']:<6} | {avg_rtf:<5}")
        else:
            print(f"{m:<18} | {'FAIL':<44}")

    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
