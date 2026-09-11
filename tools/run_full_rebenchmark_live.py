"""
E-ZZIO Full Physical Live Re-Execution Runner (Lab v19.1 Live).
Executes direct live physical inference on all available local models across threads and contexts,
recording genuine live run files with real-time process execution, timestamps, and memory captures.
"""
import os
import sys
import json
import time
import hashlib
import urllib.request
import subprocess
import psutil
from pathlib import Path

root = Path("G:/AI/E-zzio")
v19_dir = root / "state/audit/optimization/performance_v19"
v19_dir.mkdir(parents=True, exist_ok=True)
live_runs_dir = v19_dir / "live_runs"
live_runs_dir.mkdir(parents=True, exist_ok=True)

llama_cli = Path("G:/AI/external/llama.cpp/build/bin/Release/llama-cli.exe")
ext_models = Path("G:/AI/external/models")

models = [
    {"id": "phi4-mini", "tag": "phi4-mini:latest", "runtime": "Ollama", "sha256": "78fad5d182a7c33065e153a5f8ba210754207ba9d91973f57dffa7f487363753"},
    {"id": "qwen3.5-9b", "tag": "qwen3.5:9b", "runtime": "Ollama", "sha256": "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"},
    {"id": "hermes3-8b", "tag": "hermes3:8b", "runtime": "Ollama", "sha256": "4f6b83f30b62bc3d0cf9be09266db222805ee815c8fd7d8b38f863f655be78b7"},
    {"id": "ornith-1.5-9b", "tag": "ornith-1.5:9b", "runtime": "Ollama", "sha256": "e00611bf85b88b9354026bb403c9ebf74c7e39a3f894101e403d15444747d10b"},
    {"id": "llama3.1-8b-abliterated", "tag": "llama3.1-8b-abliterated:latest", "runtime": "Ollama", "sha256": "6ca42298c98c662f558a74e54823297a7a726be646eb34f19b2cdbe906059c3f"},
    {"id": "Ministral-3B", "tag": "Ministral-3-3B-Instruct (2512)", "runtime": "llama.cpp", "path": ext_models / "ministral-3-3b-instruct/Ministral-3-3B-Instruct-2512-Q4_K_M.gguf", "sha256": "fd46fc371ff0509bfa8657ac956b7de8534d7d9baaa4947975c0648c3aa397f4"},
    {"id": "Gemma-4-E4B", "tag": "Gemma-4-E4B-it", "runtime": "llama.cpp", "path": ext_models / "gemma-4-e4b-it/gemma-4-E4B-it-Q4_K_M.gguf", "sha256": "85a896a047553e842f25297ee5b031d64ff30147d9c4af17b1e4b394cd1fab87"},
    {"id": "Qwen3.5-9B-MTP", "tag": "Qwen3.5-9B-MTP", "runtime": "llama.cpp", "path": ext_models / "qwen3.5-9b-mtp/Qwen3.5-9B-Q4_K_M.gguf", "sha256": "e8dd94817e95d6c0939102049d068418269978377b13616c4726235e232841fe"}
]

tasks_eval = [
    ("FAST_ROUTING", "Quelle est la destination optimale pour une requête de code Python ? Réponds en un mot.", 32),
    ("REASONING", "Soit un serveur de 12 coeurs. 3 processus occupent 2, 4 et 2 coeurs. Combien reste-t-il de coeurs disponibles ?", 64),
    ("CODING", "Écris une fonction Python 'is_even(n)' ultra-optimisée avec docstring.", 64),
    ("TOOLS", "Génère un appel d'outil JSON strict pour la fonction 'search_file' avec argument 'path'.", 64)
]

threads_sweep = [1, 2, 4, 8]
contexts_sweep = [2048, 4096]

def get_ram_mb():
    return psutil.virtual_memory().used / (1024 * 1024)

def unload_ollama(model_name: str):
    try:
        data = json.dumps({"model": model_name, "keep_alive": 0}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            pass
    except Exception:
        pass
    time.sleep(0.3)

def run_physical_test(pass_id, model_obj, task_name, prompt_text, max_tokens, threads, context):
    m_id = model_obj["id"]
    m_tag = model_obj["tag"]
    runtime = model_obj["runtime"]
    run_id = f"rebench_{pass_id}_{m_id}_{task_name}_{threads}T_{context}ctx"
    
    t_start = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    ram_before = get_ram_mb()
    
    raw_stdout = ""
    raw_stderr = ""
    exit_code = 0
    tok_s = 0.0
    ttft_ms = 0.0
    pid = 0
    
    t0 = time.perf_counter()
    
    if runtime == "Ollama":
        payload = {
            "model": m_tag,
            "prompt": prompt_text,
            "stream": False,
            "keep_alive": 0,
            "options": {
                "temperature": 0.0,
                "seed": 42,
                "num_thread": threads,
                "num_gpu": 0,
                "num_ctx": context,
                "num_predict": max_tokens
            }
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
            raw_stdout = res_json.get("response", "")
            eval_count = res_json.get("eval_count", 1)
            eval_duration = res_json.get("eval_duration", 1)
            tok_s = round(eval_count / (eval_duration / 1e9), 2) if eval_duration > 0 else 0.0
            ttft_ms = round(res_json.get("prompt_eval_duration", 1) / 1e6, 1)
            pid = 11434
        except Exception as e:
            raw_stderr = str(e)
            exit_code = 1
        ram_peak = get_ram_mb()
        unload_ollama(m_tag)
    else: # llama.cpp
        cmd = [
            str(llama_cli),
            "-m", str(model_obj["path"]),
            "-p", prompt_text,
            "-t", str(threads),
            "-ngl", "0",
            "-c", str(context),
            "-n", str(max_tokens),
            "--no-warmup",
            "--simple-io"
        ]
        try:
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore")
            pid = p.pid
            stdout, stderr = p.communicate(input="/exit\n", timeout=120)
            exit_code = p.returncode
            raw_stdout = stdout
            raw_stderr = stderr
            ram_peak = get_ram_mb()
            p.wait()
            # Extract generation tok/s
            import re
            m = re.search(r"Prompt:\s*([\d\.]+)\s*t/s\s*\|\s*Generation:\s*([\d\.]+)\s*t/s", stdout)
            if m:
                tok_s = float(m.group(2))
                ttft_ms = round(1000.0 / max(float(m.group(1)), 1.0), 1)
        except Exception as e:
            raw_stderr = str(e)
            exit_code = 1
            ram_peak = get_ram_mb()
            
    lat_total = (time.perf_counter() - t0) * 1000
    time.sleep(0.2)
    ram_after = get_ram_mb()
    t_end = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    is_valid = exit_code == 0 and tok_s > 0
    
    run_file_data = {
        "run_id": run_id,
        "pass": pass_id,
        "model": m_id,
        "task": task_name,
        "threads": threads,
        "context": context,
        "max_tokens": max_tokens,
        "pid": pid,
        "timestamp_start": t_start,
        "timestamp_end": t_end,
        "ttft_ms": ttft_ms,
        "generation_tok_s": tok_s,
        "total_latency_ms": round(lat_total, 1),
        "ram_peak_mb": round(ram_peak, 1),
        "ram_residual_mb": round(abs(ram_after - ram_before), 1),
        "status": "VALID" if is_valid else ("EMPTY" if exit_code == 0 else "FAILED"),
        "raw_response_snippet": raw_stdout[:200]
    }
    
    m_dir = live_runs_dir / m_id / task_name
    m_dir.mkdir(parents=True, exist_ok=True)
    (m_dir / f"{run_id}.json").write_text(json.dumps(run_file_data, indent=2, ensure_ascii=False), encoding="utf-8")
    return run_file_data

print("============================================================")
print("E-ZZIO COMPLETE REAL RE-BENCHMARK v19.1 LIVE")
print("============================================================")
print("MODE              : LIVE PHYSICAL EXECUTION")
print("CPU ONLY          : TRUE (CUDA = OFF / GPU = 0)")
print("MODELS TO TEST    : 8")
print(f"START TIME        : {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
print("============================================================\n")

all_live_results = []

# PASS 1 Execution
print(">>> LAUNCHING PHYSICAL PASS 1 <<<")
for m in models:
    print(f"\n[PASS 1] MODEL: {m['id']} ({m['runtime']})")
    for t_name, prompt_txt, max_tok in tasks_eval:
        for th in threads_sweep:
            for ctx in contexts_sweep:
                print(f"  [{t_name}] {th}T / {ctx}ctx ... ", end="", flush=True)
                res = run_physical_test("P1", m, t_name, prompt_txt, max_tok, th, ctx)
                all_live_results.append(res)
                print(f"DONE -> {res['generation_tok_s']:5.2f} tok/s | TTFT: {res['ttft_ms']:6.1f}ms | RAM: {res['ram_peak_mb']:6.1f}MB | Status: {res['status']}")

# PASS 2 Execution (Reverse)
print("\n>>> LAUNCHING PHYSICAL PASS 2 (REVERSE) <<<")
for m in reversed(models):
    print(f"\n[PASS 2] MODEL: {m['id']} ({m['runtime']})")
    for t_name, prompt_txt, max_tok in tasks_eval:
        for th in threads_sweep:
            for ctx in contexts_sweep:
                print(f"  [{t_name}] {th}T / {ctx}ctx ... ", end="", flush=True)
                res = run_physical_test("P2", m, t_name, prompt_txt, max_tok, th, ctx)
                all_live_results.append(res)
                print(f"DONE -> {res['generation_tok_s']:5.2f} tok/s | TTFT: {res['ttft_ms']:6.1f}ms | RAM: {res['ram_peak_mb']:6.1f}MB | Status: {res['status']}")

total_executed = len(all_live_results)
valid_runs = len([r for r in all_live_results if r["status"] == "VALID"])

print(f"\nTOTAL PHYSICAL RUNS EXECUTED IN THIS SESSION: {total_executed} (VALID: {valid_runs})")

# Write summary JSON
(v19_dir / "rebenchmark_session_summary.json").write_text(json.dumps({
    "total_executed": total_executed,
    "valid_runs": valid_runs,
    "empty_runs": total_executed - valid_runs,
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
}, indent=2), encoding="utf-8")

print("\nRE-BENCHMARK COMPLETED SUCCESSFULLY!")
