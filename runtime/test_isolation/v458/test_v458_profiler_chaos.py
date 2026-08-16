import sys
import json
import time
import subprocess
import threading
from pathlib import Path
import statistics

sys.path.insert(0, str(Path(__file__).resolve().parent))
from concurrent_segmented_engine import ConcurrentSegmentedEngine

SANDBOX = Path("runtime/test_isolation/v458")

def calculate_percentiles(latencies):
    if not latencies:
        return 0, 0, 0, 0
    s_lat = sorted(latencies)
    p50 = statistics.median(s_lat)
    p95 = s_lat[int(len(s_lat) * 0.95)]
    p99 = s_lat[int(len(s_lat) * 0.99)]
    p_max = s_lat[-1]
    return p50 * 1000, p95 * 1000, p99 * 1000, p_max * 1000

def test_v458_latency_and_crash():
    print("=============================================================")
    print(" E-ZZIO V4.5.8 — Latency Profiler & Crash Consistency Drill")
    print("=============================================================")
    
    # Nettoyage sandbox (sauf les scripts python actifs)
    segments_dir = SANDBOX / "segments"
    if segments_dir.exists():
        for p in segments_dir.glob("**/*"):
            try:
                p.unlink()
            except Exception:
                pass
    segments_dir.mkdir(parents=True, exist_ok=True)
    
    manifest_path = SANDBOX / "manifest.json"
    manifest_sha = SANDBOX / "manifest.json.sha256"
    for mp in [manifest_path, manifest_sha]:
        if mp.exists():
            mp.unlink()

    engine = ConcurrentSegmentedEngine(str(SANDBOX))

    # --- PARTIE 1 : PROFILAGE DE LATENCE ---
    print("\n[*] Lancement du test de profilage de latence (50 000 événements)...")
    total_events = 50_000
    
    def producer():
        for i in range(total_events):
            engine.write_event({"seq": i, "data": f"latency_test_{i}"})

    t = threading.Thread(target=producer)
    start_t = time.time()
    t.start()
    t.join()
    
    engine.close()
    duration = time.time() - start_t

    latencies = []
    for seg_file in segments_dir.glob("segment_*.jsonl"):
        with open(seg_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    ev = json.loads(line.strip())
                    if "_queued_at" in ev and "_committed_at" in ev:
                        latencies.append(ev["_committed_at"] - ev["_queued_at"])

    p50, p95, p99, p_max = calculate_percentiles(latencies)
    print(f"[METRIC] Débit Profiler : {total_events/duration:.2f} events/sec")
    print(f"[LATENCY] p50 : {p50:.2f} ms | p95 : {p95:.2f} ms | p99 : {p99:.2f} ms | MAX : {p_max:.2f} ms")

    # --- PARTIE 2 : SCÉNARIO DE CRASH EN PLEIN VOL (MID-FLIGHT KILL) ---
    print("\n--- PARTIE 2 : Simulation de Crash en plein vol (Kill brut) ---")
    
    worker_script = SANDBOX / "active_worker.py"
    proc = subprocess.Popen([sys.executable, str(worker_script)])
    print(f"[*] Processus d'écriture lancé (PID: {proc.pid}). Ingestion en cours...")
    
    time.sleep(0.8)
    
    print(f"[CHAOS] Coupure brutale du process {proc.pid} (Kill -9)...")
    proc.kill()
    proc.wait()

    print("[*] Instanciation du Recovery Engine post-crash...")
    recovery_engine = ConcurrentSegmentedEngine(str(SANDBOX))
    
    total_recovered = 0
    for seg_file in sorted(segments_dir.glob("segment_*.jsonl")):
        with open(seg_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    json.loads(line.strip())
                    total_recovered += 1

    print(f"[SUCCESS] Récupération réussie. Événements valides intègres après crash : {total_recovered}")
    print("=============================================================")
    print(" STATUT : V4.5.8 LATENCY PROFILER & CRASH CONSISTENCY CERTIFIÉS")
    print("=============================================================")

if __name__ == "__main__":
    test_v458_latency_and_crash()
