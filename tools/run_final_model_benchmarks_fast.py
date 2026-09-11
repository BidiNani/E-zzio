"""
E-ZZIO : Benchmark CPU-Only Rapide et Déterministe pour Ministral-3B, Gemma-4-E4B et Qwen3.5-9B MTP.
"""
import os
import sys
import json
import time
import re
import subprocess
import statistics
from pathlib import Path

root = Path("G:/AI/E-zzio")
llama_cli = Path("G:/AI/external/llama.cpp/build/bin/Release/llama-cli.exe")
ext_models = Path("G:/AI/external/models")

models = [
    {
        "id": "ministral-3-3b-instruct",
        "name": "Ministral-3-3B-Instruct (2512)",
        "path": ext_models / "ministral-3-3b-instruct/Ministral-3-3B-Instruct-2512-Q4_K_M.gguf",
        "param": "3.8B",
        "quant": "Q4_K_M"
    },
    {
        "id": "gemma-4-e4b-it",
        "name": "Gemma-4-E4B-it",
        "path": ext_models / "gemma-4-e4b-it/gemma-4-E4B-it-Q4_K_M.gguf",
        "param": "4.3B",
        "quant": "Q4_K_M"
    },
    {
        "id": "qwen3.5-9b-mtp",
        "name": "Qwen3.5-9B-MTP",
        "path": ext_models / "qwen3.5-9b-mtp/Qwen3.5-9B-Q4_K_M.gguf",
        "param": "9.7B",
        "quant": "Q4_K_M"
    }
]

def benchmark_single(model_path: Path, threads: int, prompt: str = "Bonjour en 1 phrase.", max_tokens: int = 24):
    cmd = [
        str(llama_cli),
        "-m", str(model_path),
        "-p", prompt,
        "-t", str(threads),
        "-ngl", "0",
        "-c", "2048",
        "-n", str(max_tokens),
        "--no-warmup"
    ]
    t0 = time.perf_counter()
    try:
        p = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        stdout, stderr = p.communicate(timeout=45)
        lat_ms = (time.perf_counter() - t0) * 1000
        
        gen_tok_s = 0.0
        prompt_tok_s = 0.0
        m = re.search(r"Prompt:\s*([\d\.]+)\s*t/s\s*\|\s*Generation:\s*([\d\.]+)\s*t/s", stdout)
        if m:
            prompt_tok_s = float(m.group(1))
            gen_tok_s = float(m.group(2))
        
        # Extract output text
        out_txt = stdout.split(">")[-1].strip() if ">" in stdout else stdout.strip()
        return {
            "ok": True,
            "latency_ms": round(lat_ms, 2),
            "prompt_tok_s": prompt_tok_s,
            "generation_tok_s": gen_tok_s,
            "output_snippet": out_txt[:120]
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

benchmarks = {}

for m in models:
    m_id = m["id"]
    m_path = m["path"]
    print(f"=== BENCHMARKING {m['name']} ===")
    
    thread_runs = {}
    for th in [4, 8, 12]:
        res = benchmark_single(m_path, threads=th)
        thread_runs[f"threads_{th}"] = res
        print(f"  Th={th:2d} -> {res.get('generation_tok_s', 0):5.2f} tok/s | Latency={res.get('latency_ms', 0):6.1f}ms")
    
    # Run 1 reasoning test
    reason_res = benchmark_single(
        m_path,
        threads=4,
        prompt="Analyse ce problème : un script tente d'effacer /sys. Comment une autorité de sécurité sandboxée doit-elle réagir ? Réponds en 1 phrase concise.",
        max_tokens=48
    )
    
    # Run 1 JSON test
    json_res = benchmark_single(
        m_path,
        threads=4,
        prompt="Génère un JSON avec les clés 'status': 'OK', 'cpu': 'Ryzen 9'. Réponds UNIQUEMENT avec le JSON.",
        max_tokens=32
    )
    
    best_th_key = max(thread_runs.keys(), key=lambda k: thread_runs[k].get("generation_tok_s", 0))
    benchmarks[m_id] = {
        "model_info": m,
        "thread_sweep": thread_runs,
        "best_threads": int(best_th_key.split("_")[1]),
        "best_tok_s": thread_runs[best_th_key].get("generation_tok_s", 0),
        "reasoning_test": reason_res.get("output_snippet", ""),
        "json_test": json_res.get("output_snippet", "")
    }

out_p = root / "state/audit/optimization/model_cpu_benchmark_evidence.json"
out_p.parent.mkdir(parents=True, exist_ok=True)
out_p.write_text(json.dumps(benchmarks, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
print("\nBENCHMARK EVIDENCE SAVED TO:", out_p)
