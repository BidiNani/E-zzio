import asyncio
import time
import statistics
from core.providers.ollama_provider import OllamaProvider


async def send_request(provider: OllamaProvider, req_id: int):
    t0 = time.perf_counter()
    try:
        res = await provider.search("Réponds 'OK' en un mot.", max_tokens=10)
        dt = time.perf_counter() - t0
        return {"id": req_id, "success": True, "latency": dt, "text": res.get("data", {}).get("text", "")}
    except Exception as e:
        return {"id": req_id, "success": False, "latency": time.perf_counter() - t0, "error": str(e)}


async def run_batch(concurrency: int):
    provider = OllamaProvider()
    print(f"\n[*] Lancement du tir : {concurrency} requête(s) simultanée(s)...")
    t_start = time.perf_counter()

    tasks = [send_request(provider, i) for i in range(concurrency)]
    results = await asyncio.gather(*tasks)

    total_time = time.perf_counter() - t_start
    latencies = [r["latency"] for r in results if r["success"]]

    if latencies:
        avg_lat = statistics.mean(latencies)
        p50 = statistics.median(latencies)
        p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
        print(f"  -> Durée totale du batch : {total_time:.2f}s")
        print(f"  -> Latence Moyenne : {avg_lat:.2f}s | p50 : {p50:.2f}s | p95 : {p95:.2f}s")
        print(f"  -> Débit effectif : {len(latencies) / total_time:.2f} req/s")
    else:
        print("  -> Échec de toutes les requêtes du batch.")


async def main():
    print("=" * 60)
    print("     E-ZZIO — BENCHMARK DE MONTÉE EN CHARGE CPU (OLLAMA)")
    print("=" * 60)
    # Tir unitaire
    await run_batch(1)
    # Tir 2 concurrents
    await run_batch(2)
    # Tir 4 concurrents
    await run_batch(4)
    print("\n" + "=" * 60)
    print("[OK] Profilage de charge CPU terminé.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
