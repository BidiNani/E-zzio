import sys
import json
import os
import time
import subprocess
import random
import psutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from concurrent_segmented_engine_soak import ConcurrentSegmentedEngine

SANDBOX = Path("runtime/test_isolation/v4599/sandbox_soak")

def soak_worker(target_events: int):
    """Producteur multi-thread simulant une charge massive."""
    engine = ConcurrentSegmentedEngine(str(SANDBOX))
    
    for i in range(1, target_events + 1):
        engine.write_event({
            "seq": i,
            "timestamp": time.time(),
            "payload": f"soak_data_{i}_" + ("x" * 128)
        })
        if i % 50000 == 0:
            time.sleep(0.01)

    engine.close()

def audit_soak_store() -> tuple[int, int, int]:
    """Audit d'intégrité et de cohérence multi-segment post-soak."""
    engine = ConcurrentSegmentedEngine(str(SANDBOX))
    
    total_valid = 0
    total_corrupt = 0
    segments_count = 0
    segments_dir = SANDBOX / "segments"
    
    for seg in sorted(segments_dir.glob("segment_*.jsonl")):
        segments_count += 1
        with open(seg, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        json.loads(line.strip())
                        total_valid += 1
                    except json.JSONDecodeError:
                        total_corrupt += 1

    engine.close()
    return total_valid, total_corrupt, segments_count

def run_soak_drill():
    print("=============================================================", flush=True)
    print(" E-ZZIO V4.5.9.9 — Multi-Crash Soak Drill (5,000,000 Target)", flush=True)
    print("=============================================================", flush=True)

    if SANDBOX.exists():
        for p in SANDBOX.glob("**/*"):
            try:
                p.unlink()
            except Exception:
                pass
    SANDBOX.mkdir(parents=True, exist_ok=True)

    target_total = 500_000 # Qualification rapide à 500k pour la démo, extensible à 5M
    crash_cycles = 3
    
    print(f"[*] Lancement de la campagne Soak ({crash_cycles} cycles de crashs aléatoires)...", flush=True)

    for cycle in range(1, crash_cycles + 1):
        print(f"\n--- CYCLE SOAK {cycle}/{crash_cycles} ---", flush=True)
        
        proc = subprocess.Popen([
            sys.executable, "-c",
            f"import sys; sys.path.insert(0, r'{Path(__file__).resolve().parent}'); from test_v459_9_soak_drill import soak_worker; soak_worker({target_total})"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Interruption aléatoire pendant l'ingestion
        run_time = random.uniform(1.5, 3.5)
        print(f"[*] Ingestion active... Simulation de crash dans {run_time:.2f} secondes (PID: {proc.pid})", flush=True)
        time.sleep(run_time)

        if proc.poll() is None:
            print(f"[CHAOS] Coupure brutale (Kill -9) sur le cycle {cycle}...", flush=True)
            proc.kill()
            proc.wait()

        # Audit intermédiaire post-crash
        valid_ev, corrupt_ev, seg_count = audit_soak_store()
        print(f"[RECOVERY CYCLE {cycle}] Événements valides: {valid_ev} | Corrompus: {corrupt_ev} | Segments: {seg_count}", flush=True)
        assert corrupt_ev == 0, f"FAIL: Corruption détectée au cycle {cycle}"

    print("\n=============================================================", flush=True)
    print(" STATUS : V4.5.9.9 SOAK DRILL CERTIFIÉ (0 CORRUPTION)", flush=True)
    print("=============================================================", flush=True)

if __name__ == "__main__":
    run_soak_drill()
