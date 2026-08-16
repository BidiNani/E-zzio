import sys
import json
import time
import os
import psutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from runtime.memory.batch_async_writer import BatchAsyncAtomicEventWriter

STORE_DIR = Path("runtime/test_isolation/v453/sandbox_batch_benchmark")

def print_telemetry(process):
    mem_mb = process.memory_info().rss / (1024 * 1024)
    cpu_proc = process.cpu_percent(interval=None)
    cpu_sys = psutil.cpu_percent(interval=None)
    print(f"    [TELEMETRY] RAM RSS: {mem_mb:.2f} MB | CPU Process: {cpu_proc}% | CPU Sys: {cpu_sys}%")

def test_batch_performance():
    print("=============================================================")
    print(" E-ZZIO V4.5.5 — High Performance Batch Commit Benchmark")
    print("=============================================================")
    
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    store_path = STORE_DIR / "events_batch_bench.jsonl"
    
    for p in STORE_DIR.glob("*"):
        try:
            p.unlink()
        except Exception:
            pass

    process = psutil.Process(os.getpid())
    psutil.cpu_percent(interval=None) # Init

    # Instanciation du writer en mode batch (Max 500 events ou 30ms)
    writer = BatchAsyncAtomicEventWriter(str(store_path), max_batch_size=500, max_batch_delay=0.03)

    total_events = 100_000
    print(f"[*] Enfilement haute performance de {total_events} événements...")
    
    start_time = time.time()
    for i in range(1, total_events + 1):
        writer.write_event({"batch_seq": i, "payload": f"high_perf_data_{i}"})
        if i % 25_000 == 0:
            print(f"    -> {i} événements enfilés...")
            print_telemetry(process)

    print("[*] Clôture et flush complet de la file...")
    writer.close()
    duration = time.time() - start_time

    throughput = total_events / duration
    print("=============================================================")
    print(f"[METRIC] Débit Batch Global : {throughput:.2f} events/sec")
    print(f"[METRIC] Temps total d'exécution : {duration:.3f} secondes")
    print("=============================================================")

    # Assertions post-fermeture
    assert writer.closed == True, "FAIL: Le writer n'est pas marqué fermé"
    assert writer.queue.empty(), "FAIL: La queue n'est pas vide"
    assert not writer.worker_thread.is_alive(), "FAIL: Le thread worker est toujours actif"

    # Audit d'intégrité final
    print("[*] Audit d'intégrité séquentiel du journal de production...")
    count = 0
    with open(store_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                data = json.loads(line.strip())
                assert "batch_seq" in data, f"FAIL: Clé batch_seq manquante ligne {line_num}"
                count += 1

    assert count == total_events, f"FAIL: Attendu {total_events}, trouvé {count}"
    print(f"[SUCCESS] Intégrité validée : {count} / {total_events} événements intègres, 0 corruption.")
    print("=============================================================")

if __name__ == "__main__":
    test_batch_performance()
