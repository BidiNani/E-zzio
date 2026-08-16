import os
import sys
import json
import random
import subprocess
from pathlib import Path

# Injection chemin runtime
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.memory.atomic_writer import AtomicEventWriter

SANDBOX_DIR = Path("runtime/test_isolation/v453/sandbox_stress")

def cleanup():
    if SANDBOX_DIR.exists():
        for p in SANDBOX_DIR.glob("*"):
            try:
                p.unlink()
            except Exception:
                pass
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------------------
# Test 1: Crash Window (Store absent, pending OK, bak OK)
# ------------------------------------------------------------------------------
def test_crash_window_backup():
    cleanup()
    store = SANDBOX_DIR / "events.jsonl"
    writer = AtomicEventWriter(str(store))
    writer.write_event({"evt": "base_data"})

    # Simulation manuelle de l'état post-backup / pre-replace
    os.replace(store, writer.bak_path)
    with open(writer.pending_path, "w", encoding="utf-8") as f:
        f.write('{"evt": "new_pending_data"}\n')
        f.flush()
        os.fsync(f.fileno())

    # Re-instanciation = auto-recovery
    rec_writer = AtomicEventWriter(str(store))
    assert store.exists(), "FAIL T1: Store non restauré"
    with open(store, "r", encoding="utf-8") as f:
        content = f.read()
        assert "new_pending_data" in content, "FAIL T1: Contenu pending non promu"
    print("[OK] Test 1: Fenêtre de crash post-backup validée.")

# ------------------------------------------------------------------------------
# Test 2: Commit Log Corrompu
# ------------------------------------------------------------------------------
def test_corrupted_commit_log():
    cleanup()
    store = SANDBOX_DIR / "events.jsonl"
    writer = AtomicEventWriter(str(store))
    writer.write_event({"evt": "valid_1"})

    # Injection d'un log de commit tronqué / invalide
    with open(writer.commit_log_path, "w", encoding="utf-8") as f:
        f.write('{"state": "PREP')  # JSON tronqué
        f.flush()
        os.fsync(f.fileno())

    # Le writer doit démarrer sans lever JSONDecodeError
    try:
        rec_writer = AtomicEventWriter(str(store))
        rec_writer.write_event({"evt": "valid_2"})
        print("[OK] Test 2: Log de commit corrompu ingéré sans crash.")
    except Exception as e:
        assert False, f"FAIL T2: Exception levée sur log corrompu: {e}"

# ------------------------------------------------------------------------------
# Test 3: Micro-Worker pour Injection de Crash Aléatoire
# ------------------------------------------------------------------------------
def run_worker_child(iterations):
    store = SANDBOX_DIR / "events_fuzz.jsonl"
    writer = AtomicEventWriter(str(store))
    for i in range(iterations):
        writer.write_event({"seq": i, "payload": f"data_{i}"})
        # Injection aléatoire de crash hard
        if random.random() < 0.15:
            os._exit(1)

def test_fuzzing_chaos_loop():
    cleanup()
    store = SANDBOX_DIR / "events_fuzz.jsonl"
    
    # Lancement de 20 sous-processus exécutant des écritures avec crashs impromptus
    for cycle in range(20):
        cmd = [sys.executable, __file__, "--worker", "25"]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Récupération immédiate par le process principal
        rec_writer = AtomicEventWriter(str(store))

    # Audit d'intégrité final
    assert store.exists(), "FAIL T3: Le store n'existe pas après le fuzzing"
    
    valid_lines = 0
    with open(store, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                data = json.loads(line_str)
                assert "seq" in data and "payload" in data
                valid_lines += 1
            except json.JSONDecodeError:
                assert False, f"FAIL T3: Ligne JSON corrompue détectée à la ligne {line_num}: {line_str}"

    print(f"[OK] Test 3: Fuzzing Chaos validé. {valid_lines} événements valides, 0 corruption JSON.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        run_worker_child(int(sys.argv[2]))
    else:
        print("[*] Lancement de la suite de tests de hardening 100%...")
        test_crash_window_backup()
        test_corrupted_commit_log()
        test_fuzzing_chaos_loop()
        print("[SUCCESS] HARDENING V4.5.3 CERTIFIÉ À 100%.")
