import asyncio
import time
import httpx

API_URL = "http://127.0.0.1:8001/api/v1/chat"

TEST_PROMPTS = [
    {
        "label": "Test 1 — Présence / Local Chat (Court)",
        "message": "Bonjour E-ZZIO, confirme ton statut opérationnel.",
        "expected_intent": "local_chat"
    },
    {
        "label": "Test 2 — Analyse Technique (Micro-noyau)",
        "message": "Explique les avantages d'un micro-noyau par rapport à un noyau monolithique en 3 points concis.",
        "expected_intent": "local_chat"
    },
    {
        "label": "Test 3 — Escalade Délibérée (Raisonnement Complexe)",
        "message": "Analyse cette architecture globale et propose une stratégie d'optimisation mémoire.",
        "expected_intent": "deep_reasoning"
    }
]

async def run_benchmark():
    print("==================================================================")
    print("        BANC DE BENCHMARK & LATENCE — E-ZZIO COGNITIVE CHAT       ")
    print("==================================================================\n")

    async with httpx.AsyncClient(timeout=180.0) as client:
        for idx, item in enumerate(TEST_PROMPTS, 1):
            print(f"[*] {item['label']}")
            print(f"    Demande  : '{item['message']}'")
            
            payload = {
                "message": item["message"],
                "user_id": "discord_tester_01",
                "session_id": "discord_channel_dev"
            }

            t0 = time.perf_counter()
            try:
                resp = await client.post(API_URL, json=payload)
                t1 = time.perf_counter()
                elapsed = t1 - t0

                if resp.status_code == 200:
                    data = resp.json()
                    intent = data.get("intent")
                    provider = data.get("provider")
                    mode = data.get("mode")
                    reply = data.get("response", "").strip()
                    raw = data.get("data", {}).get("raw", {})
                    
                    eval_count = raw.get("eval_count", len(reply.split()))
                    eval_duration_ns = raw.get("eval_duration", 0)
                    tps = (eval_count / (eval_duration_ns / 1e9)) if eval_duration_ns > 0 else (eval_count / elapsed)

                    print(f"    [OK] Durée totale  : {elapsed:.2f} s")
                    print(f"    [OK] Intention     : {intent} (Attendu: {item['expected_intent']})")
                    print(f"    [OK] Fournisseur   : {provider.upper()} ({mode})")
                    if tps > 0 and provider == "ollama":
                        print(f"    [OK] Débit calcul  : ~{tps:.1f} tokens/s")
                    print(f"    [OK] Réponse Embed :\n{'-'*50}\n{reply}\n{'-'*50}\n")
                else:
                    print(f"    [ERREUR HTTP] Code {resp.status_code} : {resp.text}\n")

            except Exception as exc:
                print(f"    [EXCEPTION] Échec de l'appel : {exc}\n")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
