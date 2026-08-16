import sys
import json
import time
import threading
import psutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from concurrent_segmented_engine import ConcurrentSegmentedEngine

SANDBOX = Path("runtime/test_isolation/v457/sandbox_bench")

def producer_worker(engine, producer_id, count_per_producer):
    """Worker producteur simulant l'activité CPU en amont."""
    for i in range(count_per_producer):
        event = {
            "producer_id": producer_id,
            "seq": i,
            "timestamp": time.time(),
            "payload": f"ryzen_payload_{producer_id}_{i}"
        }
        engine.write_event(event)

def test_concurrent_benchmark():
    print("=============================================================")
    print(" E-ZZIO V4.5.7 — Concurrent Batch Ingestion (8 Ryzen Producers)")
    print("=============================================================")
    
    if SANDBOX.exists():
        for p in SANDBOX.glob("**/*"):
            try:
                p.unlink()
            except Exception:
                pass
    SANDBOX.mkdir(parents=True, exist_ok=True)

    # Initialisation moteur (Max segment 10 Mo pour tester les rotations multiples)
    engine = ConcurrentSegmentedEngine(str(SANDBOX), max_segment_size=10 * 1024 * 1024)

    num_producers = 8
    events_per_producer = 25_000  # Total = 200 000 événements
    total_events = num_producers * events_per_producer

    process = psutil.Process()
    psutil.cpu_percent(interval=None)

    print(f"[*] Lancement de {num_producers} threads producteurs (Total : {total_events} événements)...")
    start_time = time.time()

    threads = []
    for pid in range(num_producers):
        t = threading.Thread(target=producer_worker, args=(engine, pid, events_per_producer))
        threads.append(t)
        t.start()

    # Suivi de progression en direct
    while any(t.is_alive() for t in threads):
        q_size = engine.queue.qsize()
        mem_mb = process.memory_info().rss / (1024 * 1024)
        print(f"    [PROGRESS] Queue Depth: {q_size} | RAM (RSS): {mem_mb:.2f} MB")
        time.sleep(0.5)

    for t in threads:
        t.join()

    print("[*] Fin des producteurs. Vidage final et clôture (engine.close())...")
    engine.close()
    duration = time.time() - start_time

    throughput = total_events / duration
    cpu_sys = psutil.cpu_percent(interval=None)
    
    print("=============================================================")
    print(f"[METRIC] Débit Global Concurrent : {throughput:.2f} events/sec")
    print(f"[METRIC] Temps total d'exécution   : {duration:.3f} secondes")
    print(f"[METRIC] CPU Global Système        : {cpu_sys}%")
    print("=============================================================")

    # Audit d'intégrité global multi-segment
    print("[*] Audit d'intégrité de tous les segments générés...")
    total_found = 0
    segments_dir = SANDBOX / "segments"
    for seg_file in sorted(segments_dir.glob("segment_*.jsonl")):
        with open(seg_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    json.loads(line.strip())
                    total_found += 1

    assert total_found == total_events, f"FAIL: Attendu {total_events}, trouvé {total_found}"
    print(f"[SUCCESS] Audit validé : {total_found} / {total_events} événements intègres, 0 corruption.")
    print("=============================================================")

if __name__ == "__main__":
    test_concurrent_benchmark()
