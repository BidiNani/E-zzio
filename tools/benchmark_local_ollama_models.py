"""
E-ZZIO : Benchmark comparatif des modèles locaux Ollama (≤10B).
"""
import os
import sys
import json
import time
import httpx
from pathlib import Path

root = Path("G:/AI/E-zzio")
ollama_url = "http://127.0.0.1:11434"

test_prompts = [
    {
        "id": "chat_fr",
        "category": "Chat & Français",
        "prompt": "Bonjour, présente-toi brièvement en français en 2 phrases."
    },
    {
        "id": "json_struct",
        "category": "JSON Structuré",
        "prompt": "Génère un objet JSON valide avec les clés 'status' ('OK'), 'cpu_score' (int entre 1 et 100), et 'target' ('Ryzen 9'). Réponds UNIQUEMENT avec le JSON."
    },
    {
        "id": "reasoning_safety",
        "category": "Raisonnement & Sécurité",
        "prompt": "Un script malveillant tente d'exécuter rm -rf / sur le système. Comment une autorité de sécurité sandboxée doit-elle réagir ? Réponds en 2 points concis."
    }
]

models_to_test = [
    "ez-router:latest",
    "ez-core-safe:latest",
    "ez-agent-hermes:latest"
]

benchmark_results = {}

with httpx.Client(timeout=120.0) as client:
    for model_name in models_to_test:
        print(f"=== BENCHMARKING MODEL: {model_name} ===")
        model_scores = {"tests": [], "total_latency_ms": 0, "total_eval_tokens": 0}
        
        for t in test_prompts:
            t0 = time.perf_counter()
            payload = {
                "model": model_name,
                "prompt": t["prompt"],
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_ctx": 2048
                }
            }
            try:
                r = client.post(f"{ollama_url}/api/generate", json=payload)
                elapsed_ms = (time.perf_counter() - t0) * 1000
                
                if r.status_code == 200:
                    data = r.json()
                    response_text = data.get("response", "").strip()
                    eval_count = data.get("eval_count", 0)
                    eval_duration_ns = data.get("eval_duration", 1)
                    tok_per_sec = (eval_count / (eval_duration_ns / 1e9)) if eval_duration_ns > 0 else 0
                    
                    model_scores["tests"].append({
                        "id": t["id"],
                        "latency_ms": round(elapsed_ms, 2),
                        "eval_tokens": eval_count,
                        "tok_per_sec": round(tok_per_sec, 2),
                        "response_snippet": response_text[:120]
                    })
                    model_scores["total_latency_ms"] += elapsed_ms
                    model_scores["total_eval_tokens"] += eval_count
                else:
                    model_scores["tests"].append({
                        "id": t["id"],
                        "error": f"HTTP {r.status_code}: {r.text[:100]}"
                    })
            except Exception as exc:
                model_scores["tests"].append({
                    "id": t["id"],
                    "error": str(exc)
                })
        
        avg_tok_s = sum(x.get("tok_per_sec", 0) for x in model_scores["tests"] if "tok_per_sec" in x) / max(len(model_scores["tests"]), 1)
        model_scores["average_tokens_per_second"] = round(avg_tok_s, 2)
        benchmark_results[model_name] = model_scores

out_p = root / "state/audit/optimization/models_benchmark_evidence.json"
out_p.parent.mkdir(parents=True, exist_ok=True)
out_p.write_text(json.dumps(benchmark_results, indent=2, ensure_ascii=False), encoding="utf-8")
print("BENCHMARK COMPLETED AND SAVED TO:", out_p)
print(json.dumps(benchmark_results, indent=2, ensure_ascii=False))
