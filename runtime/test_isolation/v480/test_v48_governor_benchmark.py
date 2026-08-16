import sys
import json
import time
import uuid
import threading
import psutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from concurrent_segmented_engine_v48 import ConcurrentSegmentedEngineV48

SANDBOX = Path("runtime/test_isolation/v480/sandbox_governor")

def producer_worker(engine, producer_id: int, count_per_producer: int):
    agent_name = f"agent_worker_{producer_id:02d}"
    simulated_embedding = [round(0.001 * (i % 100), 4) for i in range(128)]
    
    for i in range(count_per_producer):
        event = {
            "event_id": str(uuid.uuid4()),
            "seq": i,
            "timestamp": time.time(),
            "agent_source": agent_name,
            "semantic_type": "GOVERNOR_TEST",
            "embedding_vector": simulated_embedding,
            "payload": "Payload d'essai d'affinité Ryzen Hardware Governor"
        }
        engine.write_event(event)

def run_governor_benchmark():
    print("=============================================================", flush=True)
    print(" E-ZZIO V4.8 — Ryzen Hardware Governor & Affinity Benchmark", flush=True)
    print("=============================================================", flush=True)

    if SANDBOX.exists():
        for p in SANDBOX.glob("**/*"):
            try:
                p.unlink()
            except Exception:
                pass
    SANDBOX.mkdir(parents=True, exist_ok=True)

    engine = ConcurrentSegmentedEngineV48(str(SANDBOX), max_segment_size=20 * 1024 * 1024)
    governor = engine.governor

    # PHASE 1 : PROFIL GAMING (CCD1 uniquement, Threads 12-23)
    print("\n--- PHASE 1 : Application du Profil GAMING (CCD1 - Threads 12-23) ---", flush=True)
    telem_gaming = governor.apply_profile("GAMING")
    print(f"[TELEMETRY GAMING] {telem_gaming}", flush=True)
    
    start_t1 = time.time()
    t1 = threading.Thread(target=producer_worker, args=(engine, 1, 50_000))
    t1.start()
    t1.join()
    dur1 = time.time() - start_t1
    print(f"[METRIC GAMING] 50,000 evts ingérés en {dur1:.2f} s ({50000/dur1:.2f} evts/sec)", flush=True)

    # PHASE 2 : PROFIL COMPUTE (CCD0 + CCD1, Threads 2-23)
    print("\n--- PHASE 2 : Basculement vers le Profil COMPUTE (Threads 2-23) ---", flush=True)
    telem_compute = governor.apply_profile("COMPUTE")
    print(f"[TELEMETRY COMPUTE] {telem_compute}", flush=True)
    
    start_t2 = time.time()
    threads_comp = []
    for pid in range(4):
        t = threading.Thread(target=producer_worker, args=(engine, pid + 2, 25_000))
        threads_comp.append(t)
        t.start()
    for t in threads_comp:
        t.join()
    dur2 = time.time() - start_t2
    print(f"[METRIC COMPUTE] 100,000 evts ingérés en {dur2:.2f} s ({100000/dur2:.2f} evts/sec)", flush=True)

    # PHASE 3 : PROFIL EVOLUTION (24 Threads Débridés)
    print("\n--- PHASE 3 : Basculement vers le Profil EVOLUTION (24 Threads) ---", flush=True)
    telem_evo = governor.apply_profile("EVOLUTION")
    print(f"[TELEMETRY EVOLUTION] {telem_evo}", flush=True)
    
    start_t3 = time.time()
    threads_evo = []
    for pid in range(8):
        t = threading.Thread(target=producer_worker, args=(engine, pid + 10, 25_000))
        threads_evo.append(t)
        t.start()
    for t in threads_evo:
        t.join()
    dur3 = time.time() - start_t3
    print(f"[METRIC EVOLUTION] 200,000 evts ingérés en {dur3:.2f} s ({200000/dur3:.2f} evts/sec)", flush=True)

    print("\n[*] Fermeture du moteur et validation de la persistance...", flush=True)
    engine.close()

    total_valid = 0
    segments_dir = SANDBOX / "segments"
    for seg in sorted(segments_dir.glob("segment_*.jsonl")):
        with open(seg, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        obj = json.loads(line.strip())
                        if obj.get("__type__") != "SEGMENT_FOOTER":
                            total_valid += 1
                    except Exception:
                        pass

    print(f"[AUDIT FINAL] Événements valides persistés sur disque : {total_valid:,} / 350,000", flush=True)
    assert total_valid == 350_000, f"FAIL: Attendu 350,000, trouvé {total_valid}"

    print("=============================================================", flush=True)
    print(" STATUS : V4.8 RYZEN HARDWARE GOVERNOR CERTIFIÉ", flush=True)
    print("=============================================================", flush=True)

if __name__ == "__main__":
    run_governor_benchmark()
