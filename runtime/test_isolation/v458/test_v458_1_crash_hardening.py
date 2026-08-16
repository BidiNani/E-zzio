import sys
import json
import time
import subprocess
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from concurrent_segmented_engine import ConcurrentSegmentedEngine

SANDBOX = Path("runtime/test_isolation/v458")

def test_crash_consistency_drill():
    print("=============================================================")
    print(" E-ZZIO V4.5.8.1 — Crash Consistency Hardened Drill")
    print("=============================================================")
    
    segments_dir = SANDBOX / "segments"
    
    # Lancement du worker d'écriture active avec capture de flux
    worker_script = SANDBOX / "active_worker.py"
    print(f"[*] Démarrage du sous-processus d'écriture active (PID en cours)...")
    
    proc = subprocess.Popen(
        [sys.executable, str(worker_script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    print(f"[OK] Processus actif démarré (PID: {proc.pid})")
    
    # Laisser alimenter les segments pendant 1.5 seconde
    time.sleep(1.5)
    
    # Vérification que le process tourne toujours
    if proc.poll() is not None:
        out, err = proc.communicate()
        print(f"[ERREUR CRITIQUE] Le worker s'est arrêté prématurément.\nSTDOUT: {out}\nSTDERR: {err}")
        sys.exit(1)

    print(f"[CHAOS] Injection d'une coupure brutale (Kill -9) sur le PID {proc.pid}...")
    proc.kill()
    try:
        stdout, stderr = proc.communicate(timeout=2)
        if stderr:
            print(f"[DIAGNOSTIC WORKER STDERR] {stderr}")
    except Exception:
        pass

    print("[*] Instanciation du Recovery Engine post-crash (Boot recovery)...")
    start_recovery = time.time()
    recovery_engine = ConcurrentSegmentedEngine(str(SANDBOX))
    recovery_duration = time.time() - start_recovery
    
    print(f"[OK] Recovery effectué en {recovery_duration * 1000:.2f} ms.")

    # Audit d'intégrité mathématique post-crash
    total_recovered = 0
    corrupted_files = 0
    
    for seg_file in sorted(segments_dir.glob("segment_*.jsonl")):
        with open(seg_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        json.loads(line.strip())
                        total_recovered += 1
                    except json.JSONDecodeError:
                        corrupted_files += 1

    assert corrupted_files == 0, f"FAIL: {corrupted_files} lignes corrompues détectées après recovery !"
    assert total_recovered > 0, "FAIL: Le store est totalement vide après crash !"

    print(f"[SUCCESS] Audit post-crash validé : {total_recovered} événements valides récupérés, 0 corruption.")
    print("=============================================================")
    print(" STATUS : V4.5.8.1 CRASH CONSISTENCY DRILL CERTIFIÉ")
    print("=============================================================")

if __name__ == "__main__":
    test_crash_consistency_drill()
