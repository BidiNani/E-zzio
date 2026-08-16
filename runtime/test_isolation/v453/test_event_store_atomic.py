import os
import sys
from pathlib import Path

# Fix import path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.memory.atomic_writer import AtomicEventWriter

def execute_crash_drill():
    store_file = Path("runtime/test_isolation/v453/sandbox_data/events_crash.jsonl")
    store_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Nettoyage
    for p in store_file.parent.glob("*"):
        p.unlink()

    writer = AtomicEventWriter(str(store_file))
    writer.write_event({"evt": 1, "status": "initial"})

    # Simulation d'écriture interrompue : écriture du pending + fsync
    pending = writer.pending_path
    with open(pending, "w", encoding="utf-8") as f:
        f.write('{"evt": 2, "status": "pending_crash"}\n')
        f.flush()
        os.fsync(f.fileno())

    # CRASH BRUTAL DU PROCESSUS PYTHON SANS RUNTIME CLEANUP
    print("[CHAOS] Injection crash os._exit(1)...")
    os._exit(1)

if __name__ == "__main__":
    execute_crash_drill()
