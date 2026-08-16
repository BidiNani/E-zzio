import sys
import asyncio
import aiohttp
import json

sys.path.insert(0, r'G:\AI\E-zzio')

print("=" * 60)
print(" E-ZZIO V7 — INSPECTION FORENSIQUE DES CHUNKS OLLAMA (R6)")
print("=" * 60)

async def inspect_ollama_stream():
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "qwen3:4b",
        "prompt": "Dis bonjour.",
        "stream": True,
        "options": {"num_predict": 32}
    }

    print(f"[CONNECT] Envoi de la requête à Ollama (Modèle: qwen3:4b)...")
    
    chunk_index = 0
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                print(f"[HTTP STATUS] {resp.status}")
                if resp.status != 200:
                    text_err = await resp.text()
                    print(f"❌ Erreur HTTP Ollama : {text_err}")
                    return

                async for line in resp.content:
                    if line:
                        chunk_index += 1
                        raw_str = line.decode('utf-8').strip()
                        try:
                            data = json.loads(raw_str)
                            keys = list(data.keys())
                            resp_val = data.get("response", None)
                            think_val = data.get("thinking", None)
                            done_val = data.get("done", False)

                            print(f"  [Chunk #{chunk_index}] Clés: {keys} | done: {done_val}")
                            if resp_val is not None:
                                print(f"    └─ response: {repr(resp_val)}")
                            if think_val is not None:
                                print(f"    └─ thinking: {repr(think_val[:30])}...")
                            
                            if done_val:
                                print(f"  [FIN] Génération terminée par le modèle.")
                                break
                        except json.JSONDecodeError:
                            print(f"  [Chunk #{chunk_index}] Erreur de décodage JSON sur la ligne : {raw_str}")

    except Exception as e:
        print(f"❌ Exception critique réseau/API : {e}")

if __name__ == "__main__":
    asyncio.run(inspect_ollama_stream())
