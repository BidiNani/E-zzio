import sys
import json
import os
import time
import subprocess
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from concurrent_segmented_engine_faulty import ConcurrentSegmentedEngine, FaultInjector

SANDBOX = Path("runtime/test_isolation/v4598/sandbox_chaos")

def worker_mode(hook_name: str):
    """S'exécute dans un sous-processus dédié à l'injection de faute."""
    injector = FaultInjector(active_hook=hook_name)
    engine = ConcurrentSegmentedEngine(str(SANDBOX), fault_injector=injector)
    
    for i in range(1, 501):
        engine.write_event({"seq": i, "data": f"chaos_payload_{i}"})
        if i % 100 == 0:
            time.sleep(0.01)

    engine.close()

def audit_store(expected_min_events: int = 0) -> tuple[int, int]:
    """Audit d'intégrité strict du store après crash et recovery."""
    recovery_engine = ConcurrentSegmentedEngine(str(SANDBOX))
    
    total_valid = 0
    total_corrupt = 0
    segments_dir = SANDBOX / "segments"
    
    for seg in sorted(segments_dir.glob("segment_*.jsonl")):
        with open(seg, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        json.loads(line.strip())
                        total_valid += 1
                    except json.JSONDecodeError:
                        total_corrupt += 1

    recovery_engine.close()
    return total_valid, total_corrupt

def run_chaos_matrix():
    print("=============================================================", flush=True)
    print(" E-ZZIO V4.5.9.8 — Crash Matrix & Fault Injection Drill", flush=True)
    print("=============================================================", flush=True)

    hooks_to_test = [
        "PRE_WRITE",
        "PRE_FSYNC",
        "PRE_TASK_DONE",
        "PRE_MANIFEST_SWAP"
    ]

    executed_scenarios = 0
    passed_scenarios = 0

    for hook in hooks_to_test:
        executed_scenarios += 1
        print(f"\n--- TEST MATRICE ({executed_scenarios}/{len(hooks_to_test)}) : HOOK '{hook}' ---", flush=True)

        if SANDBOX.exists():
            for p in SANDBOX.glob("**/*"):
                try:
                    p.unlink()
                except Exception:
                    pass
        SANDBOX.mkdir(parents=True, exist_ok=True)

        # Lancement du worker crash sous-processus
        proc = subprocess.Popen([
            sys.executable, str(Path(__file__).resolve()), "--worker", hook
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        stdout, stderr = proc.communicate(timeout=5)
        print(f"[*] Processus worker terminé (Exitcode: {proc.returncode})", flush=True)

        assert proc.returncode != 0, f"FAIL: Le worker ne s'est pas arrêté sur l'injection '{hook}'"

        # Boot Recovery & Audit
        valid_count, corrupt_count = audit_store()
        print(f"[RECOVERY AUDIT] Événements valides : {valid_count} | Lignes corrompues : {corrupt_count}", flush=True)

        assert corrupt_count == 0, f"FAIL: {corrupt_count} corruption(s) détectée(s) après crash '{hook}'"
        
        passed_scenarios += 1
        print(f"[SUCCESS] Scénario '{hook}' validé ({passed_scenarios}/{len(hooks_to_test)}).", flush=True)

    print(f"\nEXECUTED_SCENARIOS: {executed_scenarios}", flush=True)
    print(f"PASSED_SCENARIOS: {passed_scenarios}", flush=True)

    if executed_scenarios == len(hooks_to_test) and passed_scenarios == len(hooks_to_test):
        print("=============================================================", flush=True)
        print(" STATUS : V4.5.9.8 CHAOS MATRIX CERTIFIÉE (0 CORRUPTION)", flush=True)
        print("=============================================================", flush=True)
    else:
        raise RuntimeError(f"CERTIFICATION REFUSÉE : {passed_scenarios}/{executed_scenarios} scénarios validés.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", type=str, help="Exécute le mode worker sur un hook spécifique")
    args = parser.parse_args()

    if args.worker:
        worker_mode(args.worker)
    else:
        run_chaos_matrix()
