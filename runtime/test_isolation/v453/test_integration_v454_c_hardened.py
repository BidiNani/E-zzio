import sys
import json
import time
import os
import psutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from runtime.test_isolation.v453.async_atomic_writer import AsyncAtomicEventWriter

STORE_DIR = Path("runtime/test_isolation/v453/sandbox_ryzen_drill")

def print_memory_usage():
    process = psutil.Process(os.getpid())
    mem_mb = process.memory_info().rss / (1024 * 1024)
    print(f"    [METRIC] RAM (RSS): {mem_mb:.2f} MB")

def test_ryzen_async_drill():
    print("=============================================================")
    print(" E-ZZIO V4.5.4 — Ryzen 5900X Async Endurance & Queue Monitor")
    print("=============================================================")
    
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    store_path = STORE_DIR / "events_ryzen_drill.jsonl"
    
    for p in STORE_DIR.glob("*"):
        try:
            p.unlink()
        except Exception:
            pass

    writer = AsyncAtomicEventWriter(str(store_path))

    # Phase 1 : 10k events
    print("\n[*] Phase 1 : Qualification rapide (10k events)...")
    start_p1 = time.time()
    for i in range(1, 10_001):
        writer.write_event({"phase": 1, "seq": i})
    writer.flush()
    dur_p1 = time.time() - start_p1
    print(f"[OK] Phase 1 : {10000/dur_p1:.2f} events/sec")
    print_memory_usage()

    # Phase 2 : 100k events avec monitoring de la queue
    print("\n[*] Phase 2 : Charge endurance (100k events) avec monitoring queue...")
    start_p2 = time.time()
    for i in range(10_001, 110_001):
        writer.write_event({"phase": 2, "seq": i})
        if i % 25_000 == 0:
            q_size = writer.queue.qsize()
            print(f"    -> {i - 10000} events enfilés | Queue Depth: {q_size}")
            print_memory_usage()
    
    print("[*] Synchronisation et fermeture propre (writer.close())...")
    writer.close()
    
    dur_p2 = time.time() - start_p2
    throughput = 100_000 / dur_p2
    print(f"[METRIC] Débit global Phase 2 : {throughput:.2f} events/sec")

    # Assertions de sécurité post-fermeture
    assert writer.closed == True, "FAIL: L'état closed du writer n'est pas True"
    assert writer.queue.empty(), "FAIL: La file d'attente n'est pas vide après close()"
    assert not writer.worker_thread.is_alive(), "FAIL: Le thread worker est toujours actif"
    print("[OK] Assertions validées : Queue vide, thread arrêté proprement, état closed actif.")

    # Phase 3 : Audit d'intégrité
    print("\n[*] Phase 3 : Audit d'intégrité séquentiel...")
    total_expected = 110_000
    count = 0
    with open(store_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                data = json.loads(line.strip())
                assert "seq" in data, f"FAIL: Clé seq manquante ligne {line_num}"
                count += 1

    assert count == total_expected, f"FAIL: Attendu {total_expected}, trouvé {count}"
    print(f"[SUCCESS] Intégrité validée : {count} / {total_expected} événements intègres, 0 corruption.")
    print("=============================================================")
    print(" STATUS : V4.5.4 ASYNC ENDURANCE & RYZEN PIPELINE CERTIFIÉS")
    print("=============================================================")

if __name__ == "__main__":
    test_ryzen_async_drill()
