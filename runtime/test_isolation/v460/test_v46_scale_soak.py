import sys
import json
import time
import subprocess
import threading
import psutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from concurrent_segmented_engine_v46 import ConcurrentSegmentedEngineV46

SANDBOX = Path("runtime/test_isolation/v460/sandbox_scale")

def producer_thread_worker(engine, producer_id: int, count_per_producer: int):
    """Producteur simulant des charges de 512B à 2KB."""
    payload_str = "x" * 700  # Payload réaliste ~800 octets
    for i in range(count_per_producer):
        event = {
            "producer_id": producer_id,
            "seq": i,
            "timestamp": time.time(),
            "payload": f"p_{producer_id}_{i}_" + payload_str
        }
        engine.write_event(event)

def run_scale_soak():
    print("=============================================================", flush=True)
    print(" E-ZZIO V4.6.0 — Production Scale Validation (Ryzen 8 Threads)", flush=True)
    print("=============================================================", flush=True)

    if SANDBOX.exists():
        for p in SANDBOX.glob("**/*"):
            try:
                p.unlink()
            except Exception:
                pass
    SANDBOX.mkdir(parents=True, exist_ok=True)

    # Paramètres d'échelle de production V4.6.0
    num_producers = 8
    events_per_producer = 62_500  # Total 500 000 événements par sous-session
    total_events = num_producers * events_per_producer
    
    # Intégration de segments de 10 Mo pour tester les rotations fréquentes et les footers
    engine = ConcurrentSegmentedEngineV46(str(SANDBOX), max_segment_size=10 * 1024 * 1024)

    process = psutil.Process()
    psutil.cpu_percent(interval=None)

    print(f"[*] Démarrage de {num_producers} producteurs parallèles ({total_events} événements)...", flush=True)
    start_t = time.time()

    threads = []
    for pid in range(num_producers):
        t = threading.Thread(target=producer_thread_worker, args=(engine, pid, events_per_producer))
        threads.append(t)
        t.start()

    while any(t.is_alive() for t in threads):
        q_len = engine.queue.qsize()
        rss_mb = process.memory_info().rss / (1024 * 1024)
        print(f"    [MONITOR] Queue: {q_len} items | RAM RSS: {rss_mb:.2f} MB", flush=True)
        time.sleep(0.5)

    for t in threads:
        t.join()

    print("[*] Vidage final et scellement du moteur...", flush=True)
    engine.close()
    duration = time.time() - start_t
    throughput = total_events / duration

    print("-------------------------------------------------------------", flush=True)
    print(f"[METRIC] Débit Brut V4.6.0    : {throughput:.2f} events/sec", flush=True)
    print(f"[METRIC] Empreinte Mémoire RSS : {process.memory_info().rss / (1024 * 1024):.2f} MB", flush=True)
    print("-------------------------------------------------------------", flush=True)

    # Audit d'intégrité et validation des Footers
    print("[*] Inspection et audit d'intégrité des segments et footers...", flush=True)
    total_valid = 0
    total_corrupt = 0
    footers_found = 0
    
    segments_dir = SANDBOX / "segments"
    for seg in sorted(segments_dir.glob("segment_*.jsonl")):
        with open(seg, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        obj = json.loads(line.strip())
                        if isinstance(obj, dict) and obj.get("__type__") == "SEGMENT_FOOTER":
                            footers_found += 1
                        else:
                            total_valid += 1
                    except json.JSONDecodeError:
                        total_corrupt += 1

    print(f"[AUDIT] Événements valides : {total_valid} / {total_events}", flush=True)
    print(f"[AUDIT] Footers détectés   : {footers_found}", flush=True)
    print(f"[AUDIT] Lignes corrompues  : {total_corrupt}", flush=True)

    assert total_corrupt == 0, f"FAIL: {total_corrupt} corruptions détectées"
    assert total_valid == total_events, f"FAIL: Attendu {total_events}, trouvé {total_valid}"
    assert footers_found > 0, "FAIL: Aucun footer de scellement détecté"

    print("=============================================================", flush=True)
    print(" STATUS : V4.6.0 PRODUCTION SCALE & FOOTERS CERTIFIÉS", flush=True)
    print("=============================================================", flush=True)

if __name__ == "__main__":
    run_scale_soak()
