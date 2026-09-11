"""
E-ZZIO : Recherche Active des Modèles Candidats sur Hugging Face API et Ollama Registry.
"""
import os
import sys
import json
import httpx
from pathlib import Path

root = Path("G:/AI/E-zzio")

queries = [
    ("qwen_3.5_mtp", "Qwen3.5-9B-MTP"),
    ("qwen_2.5_mtp", "Qwen2.5-MTP"),
    ("ministral_3b", "Ministral-3b-instruct GGUF"),
    ("ministral_8b", "Ministral-8b-instruct GGUF"),
    ("gemma_4_e4b", "Gemma 4 E4B"),
    ("gemma_2_2b", "gemma-2-2b-it GGUF"),
    ("qwen2.5_coder_7b", "Qwen2.5-Coder-7B-Instruct-GGUF"),
    ("deepseek_r1_7b", "DeepSeek-R1-Distill-Qwen-7B GGUF")
]

hf_api = "https://huggingface.co/api/models"
search_results = {}

with httpx.Client(timeout=30.0) as client:
    for key, q in queries:
        try:
            r = client.get(hf_api, params={"search": q, "limit": 5})
            if r.status_code == 200:
                data = r.json()
                models = []
                for m in data:
                    models.append({
                        "id": m.get("id"),
                        "downloads": m.get("downloads", 0),
                        "likes": m.get("likes", 0),
                        "lastModified": m.get("lastModified")
                    })
                search_results[key] = {
                    "query": q,
                    "found_count": len(models),
                    "top_models": models
                }
            else:
                search_results[key] = {"query": q, "error": f"HTTP {r.status_code}"}
        except Exception as exc:
            search_results[key] = {"query": q, "error": str(exc)}

out_p = root / "state/audit/optimization/hf_model_search_evidence.json"
out_p.parent.mkdir(parents=True, exist_ok=True)
out_p.write_text(json.dumps(search_results, indent=2, ensure_ascii=False), encoding="utf-8")
print("HF SEARCH RESULTS SAVED TO:", out_p)
print(json.dumps(search_results, indent=2, ensure_ascii=False))
