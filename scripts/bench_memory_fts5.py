"""
Benchmark statistique réel pour UnifiedMemoryGateway (SQLite WAL + FTS5).
Mesure les latences p50, p95, p99 sur insertion massive (1000 messages) et recherche textuelle FTS5.
"""
import asyncio
import time
import os
import sys
import statistics
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.memory.unified_gateway import UnifiedMemoryGateway


async def run_benchmark():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "bench_fts5.db")
        gateway = UnifiedMemoryGateway(db_path=db_path)
        await gateway.init()

        print("==================================================")
        print("     BENCHMARK STATISTIQUE UNIFIED MEMORY FTS5   ")
        print("==================================================")

        # 1. Insertion de 1 000 messages avec mesure de latence unitaire
        insert_latencies_ms = []
        sample_topics = [
            "configuration RAG et optimisation des prompts",
            "microkernels et communication IPC synchrone",
            "déploiement Docker et supervision GPU",
            "confinement de sécurité et isolation de chemin",
            "indexation SQLite WAL et recherche BM25 plein texte"
        ]

        print("[1/2] Insertion de 1 000 messages...")
        for i in range(1000):
            topic = sample_topics[i % len(sample_topics)]
            content = f"Message #{i}: Détail sur {topic} avec identifiant ref_{i*7}."
            t0 = time.perf_counter()
            await gateway.record_message(session_id=f"sess_{i % 10}", role="user" if i % 2 == 0 else "assistant", content=content)
            t1 = time.perf_counter()
            insert_latencies_ms.append((t1 - t0) * 1000)

        ins_p50 = statistics.median(insert_latencies_ms)
        ins_p95 = statistics.quantiles(insert_latencies_ms, n=20)[18]
        ins_p99 = statistics.quantiles(insert_latencies_ms, n=100)[98]
        ins_avg = statistics.mean(insert_latencies_ms)

        print(f"  ✔ Insertion 1k messages terminée.")
        print(f"    - Moyenne : {ins_avg:.2f} ms")
        print(f"    - p50     : {ins_p50:.2f} ms")
        print(f"    - p95     : {ins_p95:.2f} ms")
        print(f"    - p99     : {ins_p99:.2f} ms")

        # 2. Recherche FTS5 (100 requêtes réparties)
        search_latencies_ms = []
        queries = [
            "RAG configuration",
            "microkernels IPC",
            "confinement sécurité",
            "SQLite WAL",
            "Docker GPU",
            "identifiant ref_700",
            "optimisation prompts"
        ]

        print("\n[2/2] Exécution de 100 requêtes de recherche FTS5...")
        for i in range(100):
            q = queries[i % len(queries)]
            t0 = time.perf_counter()
            res = await gateway.search_memory(q, limit=5)
            t1 = time.perf_counter()
            search_latencies_ms.append((t1 - t0) * 1000)
            assert len(res.get("chat_history", [])) > 0

        srch_p50 = statistics.median(search_latencies_ms)
        srch_p95 = statistics.quantiles(search_latencies_ms, n=20)[18]
        srch_p99 = statistics.quantiles(search_latencies_ms, n=100)[98]
        srch_avg = statistics.mean(search_latencies_ms)

        print(f"  ✔ 100 recherches FTS5 validées (0 échec).")
        print(f"    - Moyenne : {srch_avg:.2f} ms")
        print(f"    - p50     : {srch_p50:.2f} ms")
        print(f"    - p95     : {srch_p95:.2f} ms")
        print(f"    - p99     : {srch_p99:.2f} ms")
        print("==================================================")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
