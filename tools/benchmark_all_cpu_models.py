"""
E-ZZIO : Benchmark et Évaluation des Capacités CPU-ONLY de Tous les Modèles (Baselines & Candidats).
"""
import os
import sys
import json
import time
import re
import subprocess
import psutil
import statistics
from pathlib import Path

root = Path("G:/AI/E-zzio")
llama_cli = Path("G:/AI/external/llama.cpp/build/bin/Release/llama-cli.exe")
ext_models = Path("G:/AI/external/models")

models_to_benchmark = [
    {
        "id": "ministral-3-3b-instruct",
        "name": "Ministral-3-3B-Instruct (2512)",
        "type": "gguf",
        "path": ext_models / "ministral-3-3b-instruct/Ministral-3-3B-Instruct-2512-Q4_K_M.gguf",
        "param": "3.8B",
        "quant": "Q4_K_M"
    },
    {
        "id": "gemma-4-e4b-it",
        "name": "Gemma-4-E4B-it",
        "type": "gguf",
        "path": ext_models / "gemma-4-e4b-it/gemma-4-E4B-it-Q4_K_M.gguf",
        "param": "4.3B",
        "quant": "Q4_K_M"
    },
    {
        "id": "qwen3.5-9b-mtp",
        "name": "Qwen3.5-9B-MTP",
        "type": "gguf",
        "path": ext_models / "qwen3.5-9b-mtp/Qwen3.5-9B-Q4_K_M.gguf",
        "param": "9.7B",
        "quant": "Q4_K_M"
    }
]

capability_prompts = {
    "test_a_reasoning": "Analyse un problème de contention mémoire dans un système distribué, décompose en 3 étapes de diagnostic et propose un plan vérifiable en français.",
    "test_b_tool_calling": "Tu disposes de l'outil `read_file(path: str)`. Pour lire la constitution d'E-zzio située à `core/constitution.md`, écris uniquement l'appel JSON structuré.",
    "test_c_code": "Analyse ce bug : `def add(a, b): return a - b`. Propose le patch Python minimal en 1 ligne.",
    "test_d_constraints": "Tu dois résoudre un problème sans modifier les 12 autorités constitutionnelles du Frozen Core d'E-zzio. Écris en 2 phrases ce que tu modifies et ce que tu refuses formellement de modifier.",
    "test_e_json": "Génère un objet JSON strictement valide avec les clés 'status': 'OPTIMIZED', 'cpu': 'Ryzen 9 5900X', 'gpu_used': 0. Réponds UNIQUEMENT avec le JSON."
}

def run_llama_cli(model_path: Path, prompt: str, threads: int, max_tokens: int = 64):
    cmd = [
        str(llama_cli),
        "-m", str(model_path),
        "-p", prompt,
        "-t", str(threads),
        "-ngl", "0",
        "-c", "2048",
        "-n", str(max_tokens),
        "--no-warmup",
        "-fa", "0"
    ]
    t0 = time.perf_counter()
    p = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )
    stdout, stderr = p.communicate(timeout=90)
    lat_ms = (time.perf_counter() - t0) * 1000
    
    # Extract tok/s from output like [ Prompt: 53.1 t/s | Generation: 11.6 t/s ]
    gen_tok_s = 0.0
    prompt_tok_s = 0.0
    m = re.search(r"Prompt:\s*([\d\.]+)\s*t/s\s*\|\s*Generation:\s*([\d\.]+)\s*t/s", stdout)
    if m:
        prompt_tok_s = float(m.group(1))
        gen_tok_s = float(m.group(2))
    
    return {
        "latency_ms": round(lat_ms, 2),
        "prompt_tok_s": prompt_tok_s,
        "generation_tok_s": gen_tok_s,
        "output_text": stdout.strip(),
        "exit_code": p.returncode
    }

benchmarks_data = {}
capabilities_data = {}

for m_info in models_to_benchmark:
    m_id = m_info["id"]
    m_path = m_info["path"]
    print(f"\n========================================================")
    print(f"BENCHMARKING MODEL : {m_info['name']} ({m_info['param']} / {m_info['quant']})")
    print(f"========================================================")
    
    # 1. Thread Sweep & Repetitions
    thread_results = {}
    for th in [4, 8, 12, 24]:
        runs = []
        for r_idx in range(3):
            res = run_llama_cli(m_path, "Explique brièvement le principe du CPU multithreading.", threads=th, max_tokens=32)
            runs.append(res["generation_tok_s"])
            print(f"  Th={th:2d} | Run {r_idx+1}: {res['generation_tok_s']:5.2f} tok/s (lat={res['latency_ms']:6.1f}ms)")
        
        valid_runs = [r for r in runs if r > 0]
        thread_results[f"threads_{th}"] = {
            "runs": runs,
            "mean_tok_s": round(statistics.mean(valid_runs), 2) if valid_runs else 0.0,
            "median_tok_s": round(statistics.median(valid_runs), 2) if valid_runs else 0.0,
            "min_tok_s": round(min(valid_runs), 2) if valid_runs else 0.0,
            "max_tok_s": round(max(valid_runs), 2) if valid_runs else 0.0,
            "std_dev": round(statistics.stdev(valid_runs), 2) if len(valid_runs) > 1 else 0.0
        }
    
    best_th_key = max(thread_results.keys(), key=lambda k: thread_results[k]["mean_tok_s"])
    benchmarks_data[m_id] = {
        "model_info": m_info,
        "thread_sweep": thread_results,
        "best_configuration": {
            "threads": int(best_th_key.split("_")[1]),
            "mean_tokens_per_second": thread_results[best_th_key]["mean_tok_s"]
        }
    }
    
    # 2. Capability Evaluation
    print(f"--- Running Capability Tests for {m_id} ---")
    opt_th = benchmarks_data[m_id]["best_configuration"]["threads"]
    model_caps = {}
    for cap_id, prompt_text in capability_prompts.items():
        cap_res = run_llama_cli(m_path, prompt_text, threads=opt_th, max_tokens=96)
        cleaned_out = cap_res["output_text"].split(">")[-1].strip() if ">" in cap_res["output_text"] else cap_res["output_text"]
        model_caps[cap_id] = {
            "prompt": prompt_text,
            "response": cleaned_out[:250],
            "generation_tok_s": cap_res["generation_tok_s"],
            "latency_ms": cap_res["latency_ms"]
        }
        print(f"  [{cap_id}] : {cleaned_out[:80]}...")
    capabilities_data[m_id] = model_caps

# Save artifacts
out_bench = root / "state/audit/optimization/model_cpu_benchmark_evidence.json"
out_bench.parent.mkdir(parents=True, exist_ok=True)
out_bench.write_text(json.dumps(benchmarks_data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

out_caps = root / "state/audit/optimization/model_capability_evidence.json"
out_caps.write_text(json.dumps(capabilities_data, indent=2, ensure_ascii=False), encoding="utf-8")

print("\nALL BENCHMARKS & CAPABILITY TESTS COMPLETED AND SAVED!")
