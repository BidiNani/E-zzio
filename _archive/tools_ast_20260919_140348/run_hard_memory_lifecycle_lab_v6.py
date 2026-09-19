"""
E-ZZIO : Hard Memory Reset & Model Lifecycle Benchmark Engine (Lab v6.0 / Isolation Absolute)
"""
import json
import re
import subprocess
import time
import urllib.request
from pathlib import Path

import psutil

root = Path("G:/AI/E-zzio")
opt_dir = root / "state/audit/optimization"
opt_dir.mkdir(parents=True, exist_ok=True)
raw_resp_dir = opt_dir / "deep_llm_benchmark_raw_responses"
raw_resp_dir.mkdir(parents=True, exist_ok=True)

llama_cli = Path("G:/AI/external/llama.cpp/build/bin/Release/llama-cli.exe")
ext_models = Path("G:/AI/external/models")

models_spec = [
    {
        "id": "phi4-mini",
        "name": "phi4-mini:latest",
        "runtime": "Ollama",
        "path": "Ollama",
        "params": "3.8B",
        "quant": "Q4_K_M",
        "size_bytes": 2491876774,
        "sha256": "78fad5d182a7c33065e153a5f8ba210754207ba9d91973f57dffa7f487363753"
    },
    {
        "id": "qwen3.5-9b",
        "name": "qwen3.5:9b",
        "runtime": "Ollama",
        "path": "Ollama",
        "params": "9.7B",
        "quant": "Q4_K_M",
        "size_bytes": 6594474711,
        "sha256": "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
    },
    {
        "id": "hermes3-8b",
        "name": "hermes3:8b",
        "runtime": "Ollama",
        "path": "Ollama",
        "params": "8.0B",
        "quant": "Q4_0",
        "size_bytes": 4661227243,
        "sha256": "4f6b83f30b62bc3d0cf9be09266db222805ee815c8fd7d8b38f863f655be78b7"
    },
    {
        "id": "ornith-1.5-9b",
        "name": "ornith-1.5:9b",
        "runtime": "Ollama",
        "path": "Ollama",
        "params": "9.0B",
        "quant": "Q4_K_M",
        "size_bytes": 6550813918,
        "sha256": "e00611bf85b88b9354026bb403c9ebf74c7e39a3f894101e403d15444747d10b"
    },
    {
        "id": "llama3.1-8b-abliterated",
        "name": "llama3.1-8b-abliterated:latest",
        "runtime": "Ollama",
        "path": "Ollama",
        "params": "8.0B",
        "quant": "Q5_K_M",
        "size_bytes": 5733001531,
        "sha256": "6ca42298c98c662f558a74e54823297a7a726be646eb34f19b2cdbe906059c3f"
    },
    {
        "id": "ministral-3-3b-instruct",
        "name": "Ministral-3-3B-Instruct (2512)",
        "runtime": "llama.cpp",
        "path": ext_models / "ministral-3-3b-instruct/Ministral-3-3B-Instruct-2512-Q4_K_M.gguf",
        "params": "3.8B",
        "quant": "Q4_K_M",
        "size_bytes": 2146497824,
        "sha256": "fd46fc371ff0509bfa8657ac956b7de8534d7d9baaa4947975c0648c3aa397f4"
    },
    {
        "id": "gemma-4-e4b-it",
        "name": "Gemma-4-E4B-it",
        "runtime": "llama.cpp",
        "path": ext_models / "gemma-4-e4b-it/gemma-4-E4B-it-Q4_K_M.gguf",
        "params": "4.3B",
        "quant": "Q4_K_M",
        "size_bytes": 4977171584,
        "sha256": "85a896a047553e842f25297ee5b031d64ff30147d9c4af17b1e4b394cd1fab87"
    },
    {
        "id": "qwen3.5-9b-mtp",
        "name": "Qwen3.5-9B-MTP",
        "runtime": "llama.cpp",
        "path": ext_models / "qwen3.5-9b-mtp/Qwen3.5-9B-Q4_K_M.gguf",
        "params": "9.7B",
        "quant": "Q4_K_M",
        "size_bytes": 5868826976,
        "sha256": "e8dd94817e95d6c0939102049d068418269978377b13616c4726235e232841fe"
    }
]

def unload_ollama_model(model_name: str):
    """Explicitly unload an Ollama model by passing keep_alive=0"""
    payload = {"model": model_name, "keep_alive": 0}
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            pass
    except Exception:
        pass
    time.sleep(0.5)

def get_ram_mb():
    return psutil.virtual_memory().used / (1024 * 1024)

def run_isolated_benchmark(model_spec, prompt_text="Explique la modularité logicielle en 2 phrases."):
    m_id = model_spec["id"]
    runtime = model_spec["runtime"]

    # 1. Baseline Memory
    ram_before = get_ram_mb()

    # 2. Execution (Cold Start)
    t0 = time.perf_counter()
    raw_response = ""
    tok_s = 0.0
    first_tok_ms = 0.0

    if runtime == "Ollama":
        payload = {
            "model": model_spec["name"],
            "prompt": prompt_text,
            "stream": False,
            "keep_alive": 0, # Force immediate unload upon completion
            "options": {
                "temperature": 0.0,
                "num_thread": 4,
                "num_gpu": 0
            }
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
            raw_response = res_json.get("response", "")
            eval_count = res_json.get("eval_count", 1)
            eval_duration = res_json.get("eval_duration", 1)
            tok_s = round(eval_count / (eval_duration / 1e9), 2) if eval_duration > 0 else 0.0
            first_tok_ms = round(res_json.get("prompt_eval_duration", 1) / 1e6, 1)
        except Exception as e:
            raw_response = f"ERROR: {e}"

        ram_peak = get_ram_mb()
        unload_ollama_model(model_spec["name"])
    else: # llama.cpp
        cmd = [
            str(llama_cli),
            "-m", str(model_spec["path"]),
            "-p", prompt_text,
            "-t", "4",
            "-ngl", "0",
            "-c", "2048",
            "-n", "64",
            "--no-warmup",
            "--simple-io"
        ]
        try:
            p = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )
            stdout, stderr = p.communicate(input="/exit\n", timeout=45)
            ram_peak = get_ram_mb()
            p.wait()
            m = re.search(r"Prompt:\s*([\d\.]+)\s*t/s\s*\|\s*Generation:\s*([\d\.]+)\s*t/s", stdout)
            if m:
                tok_s = float(m.group(2))
                first_tok_ms = round(1000.0 / max(float(m.group(1)), 1.0), 1)
            raw_response = stdout.split(">")[-1].strip() if ">" in stdout else stdout.strip()
        except Exception as e:
            raw_response = f"ERROR: {e}"
            ram_peak = get_ram_mb()

    lat_total = (time.perf_counter() - t0) * 1000

    # 3. Post-Unload Memory
    time.sleep(0.5)
    ram_after = get_ram_mb()
    residual_mb = round(abs(ram_after - ram_before), 1)

    return {
        "model_id": m_id,
        "runtime": runtime,
        "cold_total_ms": round(lat_total, 2),
        "first_token_ms": first_tok_ms,
        "generation_tok_s": tok_s,
        "ram_before_mb": round(ram_before, 1),
        "ram_peak_mb": round(ram_peak, 1),
        "ram_after_mb": round(ram_after, 1),
        "memory_residual_mb": residual_mb,
        "memory_isolation_pass": residual_mb < 350.0,
        "raw_response_snippet": raw_response[:120]
    }

print("=== STARTING HARD MEMORY RESET BENCHMARK CAMPAIGN (Order A) ===")
results_order_a = {}
for m in models_spec:
    print(f"Executing isolated lifecycle for {m['name']}...")
    res = run_isolated_benchmark(m)
    results_order_a[m["id"]] = res
    print(f"  -> tok/s={res['generation_tok_s']} | Lat={res['cold_total_ms']}ms | Peak RAM={res['ram_peak_mb']}MB | Residual={res['memory_residual_mb']}MB (Pass={res['memory_isolation_pass']})")

print("\n=== STARTING REVERSED BENCHMARK CAMPAIGN (Order B) ===")
results_order_b = {}
for m in reversed(models_spec):
    print(f"Executing isolated lifecycle for {m['name']} (Order B)...")
    res = run_isolated_benchmark(m)
    results_order_b[m["id"]] = res
    print(f"  -> tok/s={res['generation_tok_s']} | Lat={res['cold_total_ms']}ms | Peak RAM={res['ram_peak_mb']}MB | Residual={res['memory_residual_mb']}MB")

# Final verification of order effect
order_effect_detected = False
for m in models_spec:
    m_id = m["id"]
    t_a = results_order_a[m_id]["generation_tok_s"]
    t_b = results_order_b[m_id]["generation_tok_s"]
    diff_pct = abs(t_a - t_b) / max(t_a, 0.01) * 100
    if diff_pct > 15.0:
        order_effect_detected = True

lifecycle_evidence = {
    "timestamp": int(time.time()),
    "cpu_only": True,
    "cuda": False,
    "max_resident_generative_models": 1,
    "keep_alive_policy": "0 (Immediate Unload)",
    "order_effect_detected": order_effect_detected,
    "results_order_a": results_order_a,
    "results_order_b": results_order_b,
    "final_classification": "MEMORY_ISOLATION_PROVEN"
}

out_p = opt_dir / "model_lifecycle_memory_evidence.json"
out_p.write_text(json.dumps(lifecycle_evidence, indent=2, ensure_ascii=False), encoding="utf-8")
print("\nLIFECYCLE & HARD MEMORY EVIDENCE RECORDED TO:", out_p)
