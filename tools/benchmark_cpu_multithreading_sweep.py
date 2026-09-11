"""
E-ZZIO : CPU Parallelism & Multi-Threading Sweep Benchmark on AMD Ryzen 9 5900X (12C / 24T).
Strict CPU-ONLY (GPU = 0, CUDA = OFF, GPU_LAYERS = 0, CUDA_VISIBLE_DEVICES = -1).
"""
import os
import sys
import json
import time
import psutil
import asyncio
import numpy as np
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

root = Path("G:/AI/E-zzio")
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

# Force CPU ONLY in environment
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"

cpu_info = {
    "cpu_model": "AMD Ryzen 9 5900X",
    "physical_cores": psutil.cpu_count(logical=False),
    "logical_threads": psutil.cpu_count(logical=True),
    "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
    "gpu_usage": 0,
    "cuda_usage": 0,
    "gpu_offload": 0,
    "benchmark_mode": "CPU_ONLY"
}

thread_sweep = [1, 4, 8, 12, 16, 20, 24]
results = {"hardware": cpu_info, "benchmarks": {}}

# ==============================================================================
# 1. KOKORO-82M ONNX INTRA-OP THREADS SWEEP
# ==============================================================================
print("=== 1. BENCHMARKING KOKORO-82M ONNX THREAD SWEEP ===")
import onnxruntime as ort
import soundfile as sf
from kokoro_onnx import Kokoro

model_p = "G:/AI/external/capabilities/kokoro-tts/models/kokoro-v0_19.onnx"
voices_p = "G:/AI/external/capabilities/kokoro-tts/voices/voices.bin"
kokoro_test_phrase = "Test de parallélisme CPU sur processeur Ryzen 9 5900X."

kokoro_results = []
for th in thread_sweep:
    t0 = time.perf_counter()
    so = ort.SessionOptions()
    so.intra_op_num_threads = th
    so.inter_op_num_threads = 1
    so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    
    session = ort.InferenceSession(model_p, sess_options=so, providers=["CPUExecutionProvider"])
    k = Kokoro.from_session(session, voices_p)
    
    s, sr = k.create(kokoro_test_phrase, voice="af_bella", speed=1.0, lang="fr-fr")
    lat_ms = (time.perf_counter() - t0) * 1000
    dur_s = len(s) / sr
    rtf = (lat_ms / 1000.0) / dur_s
    
    kokoro_results.append({
        "threads": th,
        "latency_ms": round(lat_ms, 2),
        "duration_sec": round(dur_s, 2),
        "rtf": round(rtf, 4),
        "speedup_vs_1t": None # Calculated later
    })
    print(f"  Kokoro Threads={th:2d} -> Latency={lat_ms:6.1f}ms | RTF={rtf:.4f}")

base_lat = kokoro_results[0]["latency_ms"]
for r in kokoro_results:
    r["speedup_vs_1t"] = round(base_lat / max(r["latency_ms"], 0.1), 2)

best_kokoro = min(kokoro_results, key=lambda x: x["latency_ms"])
results["benchmarks"]["kokoro_tts"] = {
    "sweep": kokoro_results,
    "best_threads": best_kokoro["threads"],
    "best_latency_ms": best_kokoro["latency_ms"],
    "best_rtf": best_kokoro["rtf"]
}

# ==============================================================================
# 2. UNIVERSAL READER CONCURRENT INGESTION SWEEP
# ==============================================================================
print("\n=== 2. BENCHMARKING UNIVERSAL READER CONCURRENT INGESTION ===")
from core.perception.universal_reader import UniversalFileReader
ufr = UniversalFileReader()
# Find sample test files in repo
sample_files = list(root.glob("core/**/*.py"))[:50]

reader_results = []
for workers in [1, 2, 4, 8, 12, 16, 20, 24]:
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futs = [executor.submit(ufr.read_file, p) for p in sample_files]
        for f in futs: f.result()
    lat_ms = (time.perf_counter() - t0) * 1000
    throughput = len(sample_files) / (lat_ms / 1000.0)
    
    reader_results.append({
        "workers": workers,
        "total_latency_ms": round(lat_ms, 2),
        "files_count": len(sample_files),
        "throughput_files_per_sec": round(throughput, 1)
    })
    print(f"  UniversalReader Workers={workers:2d} -> Latency={lat_ms:5.1f}ms | Throughput={throughput:6.1f} files/s")

best_reader = max(reader_results, key=lambda x: x["throughput_files_per_sec"])
results["benchmarks"]["universal_reader"] = {
    "sweep": reader_results,
    "best_workers": best_reader["workers"],
    "best_throughput_files_per_sec": best_reader["throughput_files_per_sec"]
}

# ==============================================================================
# 3. AST CODEBASE INTROSPECTION SWEEP
# ==============================================================================
print("\n=== 3. BENCHMARKING AST INTROSPECTION SWEEP ===")
import ast

def parse_ast_file(p: Path):
    try:
        tree = ast.parse(p.read_text(encoding="utf-8", errors="ignore"))
        classes = len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)])
        functions = len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)])
        return classes + functions
    except Exception:
        return 0

all_py_files = [p for p in root.rglob("*.py") if ".venv" not in str(p) and "__pycache__" not in str(p)][:150]

ast_results = []
for workers in [1, 2, 4, 8, 12, 16, 20, 24]:
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        res = list(executor.map(parse_ast_file, all_py_files))
    lat_ms = (time.perf_counter() - t0) * 1000
    throughput = len(all_py_files) / (lat_ms / 1000.0)
    ast_results.append({
        "workers": workers,
        "files_parsed": len(all_py_files),
        "total_symbols_extracted": sum(res),
        "total_latency_ms": round(lat_ms, 2),
        "throughput_files_per_sec": round(throughput, 1)
    })
    print(f"  AST Parser Workers={workers:2d} -> Latency={lat_ms:5.1f}ms | Throughput={throughput:6.1f} files/s")

best_ast = max(ast_results, key=lambda x: x["throughput_files_per_sec"])
results["benchmarks"]["ast_introspection"] = {
    "sweep": ast_results,
    "best_workers": best_ast["workers"],
    "best_throughput_files_per_sec": best_ast["throughput_files_per_sec"]
}

# ==============================================================================
# 4. OLLAMA LLM CPU THREAD SWEEP (phi4-mini & qwen3.5:9b)
# ==============================================================================
print("\n=== 4. BENCHMARKING OLLAMA CPU NUM_THREAD SWEEP ===")
import httpx
ollama_url = "http://127.0.0.1:11434"

ollama_results = {}
models_to_test = [("ez-router:latest", "phi4-mini-3.8b"), ("ez-core-safe:latest", "qwen3.5-9b")]

with httpx.Client(timeout=180.0) as client:
    for model_tag, friendly_name in models_to_test:
        print(f"--- Model: {friendly_name} ({model_tag}) ---")
        m_sweep = []
        for th in [4, 8, 12, 16, 20, 24]:
            t0 = time.perf_counter()
            payload = {
                "model": model_tag,
                "prompt": "Explique en 2 phrases simples le principe du multithreading CPU sur un processeur 12 cœurs.",
                "stream": False,
                "options": {
                    "num_gpu": 0,
                    "num_thread": th,
                    "temperature": 0.1,
                    "num_ctx": 2048
                }
            }
            try:
                r = client.post(f"{ollama_url}/api/generate", json=payload)
                elapsed_ms = (time.perf_counter() - t0) * 1000
                if r.status_code == 200:
                    d = r.json()
                    eval_cnt = d.get("eval_count", 0)
                    eval_dur = d.get("eval_duration", 1)
                    tok_s = (eval_cnt / (eval_dur / 1e9)) if eval_dur > 0 else 0
                    m_sweep.append({
                        "threads": th,
                        "latency_ms": round(elapsed_ms, 2),
                        "tokens_per_second": round(tok_s, 2),
                        "eval_tokens": eval_cnt
                    })
                    print(f"  num_thread={th:2d} -> {tok_s:5.2f} tok/s | Latency={elapsed_ms:6.1f}ms")
                else:
                    print(f"  num_thread={th:2d} -> HTTP {r.status_code}")
            except Exception as exc:
                print(f"  num_thread={th:2d} -> Error: {exc}")
        
        if m_sweep:
            best_th = max(m_sweep, key=lambda x: x["tokens_per_second"])
            ollama_results[friendly_name] = {
                "sweep": m_sweep,
                "best_threads": best_th["threads"],
                "best_tokens_per_second": best_th["tokens_per_second"]
            }

results["benchmarks"]["ollama_llm"] = ollama_results

# ==============================================================================
# 5. SYNTHÈSE DES PROFILS OPTIMAUX
# ==============================================================================
results["recommended_profiles"] = {
    "CPU_PROFILE_LLM_ROUTER": {"model": "phi4-mini", "num_thread": ollama_results.get("phi4-mini-3.8b", {}).get("best_threads", 12)},
    "CPU_PROFILE_LLM_CORE": {"model": "qwen3.5:9b", "num_thread": ollama_results.get("qwen3.5-9b", {}).get("best_threads", 16)},
    "CPU_PROFILE_TTS_KOKORO": {"intra_op_num_threads": best_kokoro["threads"]},
    "CPU_PROFILE_INGESTION": {"workers": best_reader["workers"]},
    "CPU_PROFILE_AST": {"workers": best_ast["workers"]},
    "TOTAL_CPU_BUDGET": 24,
    "CPU_OVERSUBSCRIPTION_POLICY": "MUTEX_LLM_PRIMARY (Heavy LLM runs at 16T with max 2 concurrent workers; I/O ingestion scales to 12 workers)"
}

out_file = root / "state/audit/optimization/cpu_parallelism_evidence.json"
out_file.parent.mkdir(parents=True, exist_ok=True)
out_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
print("\nPARALLELISM SWEEP SAVED TO:", out_file)
print(json.dumps(results["recommended_profiles"], indent=2))
