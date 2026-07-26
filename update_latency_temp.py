import asyncio
import time
import json
import urllib.request
from pathlib import Path

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
LATENCY_PATH = Path("G:/AI/E-zzio/registry/model_latency.json")

async def test_model_async(model_name):
    prompt = "Réponds uniquement par le mot 'OK'."
    payload = json.dumps({
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_gpu": 0,
            "num_ctx": 1024,
            "num_predict": 10,
            "temperature": 0.1
        }
    }).encode('utf-8')
    
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
    start = time.perf_counter()
    try:
        def do_request():
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode('utf-8'))
                
        res = await asyncio.to_thread(do_request)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        reply = res.get("response", "").strip()
        
        return model_name, {
            "ok": bool(reply),
            "elapsed_ms": elapsed_ms,
            "reply": reply[:20]
        }
    except Exception as e:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return model_name, {
            "ok": False,
            "elapsed_ms": elapsed_ms,
            "error": str(e)[:50]
        }

async def run_and_save():
    req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        models = [m["name"] for m in data.get("models", [])]

    latency_data = {}
    print("📊 Test de réponse rapide :")
    for model in models:
        name, stats = await test_model_async(model)
        latency_data[name] = stats
        status_str = "✅ OK" if stats["ok"] else "❌ ERREUR"
        print(f"  • {name:<25} -> {status_str} ({stats['elapsed_ms']} ms)")

    LATENCY_PATH.parent.mkdir(parents=True, exist_ok=True)
    LATENCY_PATH.write_text(json.dumps(latency_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n💾 Registre de latence (registry/model_latency.json) mis à jour !")

if __name__ == "__main__":
    asyncio.run(run_and_save())